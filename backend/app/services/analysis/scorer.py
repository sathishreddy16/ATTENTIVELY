from __future__ import annotations

from collections.abc import Iterable

from app.services.analysis.grammar import CANONICAL_MANTRA_SLOTS, CANONICAL_MANTRA_TEXT, INTERRUPTION_TOKENS
from app.services.analysis.types import AnalysisOutcome, FlaggedMantraOutcome, NormalizedWord, ProviderResult


def _levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    prev = list(range(len(right) + 1))
    for i, char_left in enumerate(left, start=1):
        curr = [i]
        for j, char_right in enumerate(right, start=1):
            insert_cost = curr[j - 1] + 1
            delete_cost = prev[j] + 1
            replace_cost = prev[j - 1] + (char_left != char_right)
            curr.append(min(insert_cost, delete_cost, replace_cost))
        prev = curr
    return prev[-1]


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    distance = _levenshtein(left, right)
    return 1.0 - distance / max(len(left), len(right))


def _consonant_skeleton(token: str) -> str:
    normalized = _normalize_token(token)
    skeleton = []
    previous = ""
    for char in normalized:
        if char in "aeiou":
            continue
        if char != previous:
            skeleton.append(char)
            previous = char
    return "".join(skeleton)


def _normalize_token(token: str) -> str:
    return "".join(char for char in token.lower() if char.isalpha())


def _is_variant_match(token: str, allowed: tuple[str, ...]) -> bool:
    normalized = _normalize_token(token)
    return normalized in {_normalize_token(option) for option in allowed}


def _best_similarity(token: str, allowed: tuple[str, ...]) -> float:
    normalized = _normalize_token(token)
    raw = max((_similarity(normalized, _normalize_token(option)) for option in allowed), default=0.0)
    consonant = max(
        (
            _similarity(_consonant_skeleton(normalized), _consonant_skeleton(_normalize_token(option)))
            for option in allowed
        ),
        default=0.0,
    )
    return max(raw, consonant)


def _is_interruption_token(token: str) -> bool:
    return _normalize_token(token) in INTERRUPTION_TOKENS


def _window(words: list[NormalizedWord], index: int, size: int = 2) -> Iterable[NormalizedWord]:
    upper = min(len(words), index + size + 1)
    return words[index:upper]


def score_provider_result(result: ProviderResult, playback_available: bool) -> AnalysisOutcome:
    words = result.words
    outcomes: list[FlaggedMantraOutcome] = []
    final_count = 0
    yellow_flag_count = 0
    red_flag_count = 0
    gray_flag_count = 0
    pronunciation_scores: list[float] = []
    cursor = 0

    while cursor < len(words):
        start_cursor = cursor
        matched: list[tuple[int, NormalizedWord | None, str]] = []
        interruption_seen = False
        missing_slots = False
        mispronounced = False
        detected_tokens: list[str] = []

        for slot_index, allowed in enumerate(CANONICAL_MANTRA_SLOTS):
            candidate = None
            candidate_kind = "missing"

            for word in _window(words, cursor):
                token = _normalize_token(word.text)
                if not token:
                    continue
                if _is_variant_match(token, allowed):
                    candidate = word
                    candidate_kind = "exact"
                    break
                similarity = _best_similarity(token, allowed)
                if similarity >= 0.6:
                    candidate = word
                    candidate_kind = "mispronounced"
                    break
                if _is_interruption_token(token) or (word.confidence is not None and word.confidence < 0.35):
                    interruption_seen = True

            if candidate is None:
                if slot_index > 0 and allowed == CANONICAL_MANTRA_SLOTS[slot_index - 1] and matched:
                    _, prev_candidate, _ = matched[-1]
                    if prev_candidate is not None:
                        matched.append((slot_index, prev_candidate, "merged"))
                        detected_tokens.append("[merged]")
                        continue
                
                missing_slots = True
                matched.append((slot_index, None, "missing"))
                continue

            candidate_position = words.index(candidate, cursor)
            if candidate_position > cursor:
                skipped = words[cursor:candidate_position]
                if any(_is_interruption_token(item.text) or (item.confidence is not None and item.confidence < 0.35) for item in skipped):
                    interruption_seen = True
            cursor = candidate_position + 1
            detected_tokens.append(candidate.text)
            matched.append((slot_index, candidate, candidate_kind))
            if candidate_kind == "mispronounced":
                mispronounced = True
                pronunciation_scores.append(_best_similarity(candidate.text, allowed))
            else:
                pronunciation_scores.append(1.0)

        present_words = [word for _, word, _ in matched if word is not None]
        if not present_words:
            next_start = -1
            for i in range(start_cursor + 1, len(words)):
                token = _normalize_token(words[i].text)
                if token and _is_variant_match(token, CANONICAL_MANTRA_SLOTS[0]):
                    next_start = i
                    break
            cursor = next_start if next_start != -1 else len(words)
            continue

        start_sec = present_words[0].start
        end_sec = present_words[-1].end
        detected_text = " ".join(detected_tokens)

        if missing_slots:
            if interruption_seen:
                gray_flag_count += 1
                outcomes.append(
                    FlaggedMantraOutcome(
                        start_sec=start_sec,
                        end_sec=end_sec,
                        flag_color="gray",
                        issue_type="interruption",
                        expected_text=CANONICAL_MANTRA_TEXT,
                        detected_text=detected_text,
                        counted=False,
                        playback_available=playback_available,
                    )
                )
            else:
                red_flag_count += 1
                outcomes.append(
                    FlaggedMantraOutcome(
                        start_sec=start_sec,
                        end_sec=end_sec,
                        flag_color="red",
                        issue_type="missing_word",
                        expected_text=CANONICAL_MANTRA_TEXT,
                        detected_text=detected_text,
                        counted=False,
                        playback_available=playback_available,
                    )
                )
            
            # Fast-forward cursor to the next possible mantra start to prevent overlapping red flags
            next_start = -1
            for i in range(start_cursor + 1, len(words)):
                token = _normalize_token(words[i].text)
                if token and _is_variant_match(token, CANONICAL_MANTRA_SLOTS[0]):
                    next_start = i
                    break
            cursor = next_start if next_start != -1 else len(words)
        else:
            final_count += 1
            if mispronounced:
                yellow_flag_count += 1
                outcomes.append(
                    FlaggedMantraOutcome(
                        start_sec=start_sec,
                        end_sec=end_sec,
                        flag_color="yellow",
                        issue_type="pronunciation",
                        expected_text=CANONICAL_MANTRA_TEXT,
                        detected_text=detected_text,
                        counted=True,
                        playback_available=playback_available,
                    )
                )

    pronunciation_score = round((sum(pronunciation_scores) / len(pronunciation_scores)) * 100, 2) if pronunciation_scores else 0.0
    mala_count = final_count // 108
    summary_text = (
        f"Counted {final_count} mantra repetitions, {yellow_flag_count} yellow flags, "
        f"{red_flag_count} red flags, and {gray_flag_count} gray flags."
    )
    return AnalysisOutcome(
        final_count=final_count,
        mala_count=mala_count,
        yellow_flag_count=yellow_flag_count,
        red_flag_count=red_flag_count,
        gray_flag_count=gray_flag_count,
        pronunciation_score=pronunciation_score,
        summary_text=summary_text,
        flagged_mantras=outcomes,
        provider_name=result.provider_name,
        provider_version=result.provider_version,
    )
