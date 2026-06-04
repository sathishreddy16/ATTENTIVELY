from app.services.analysis.grammar import CANONICAL_MANTRA_TEXT
from app.services.analysis.scorer import score_provider_result
from app.services.analysis.types import NormalizedWord, ProviderResult


def build_result(words: list[str], confidence: float = 0.9) -> ProviderResult:
    normalized = []
    start = 0.0
    for token in words:
        end = start + 0.4
        normalized.append(
            NormalizedWord(
                text=token,
                raw_text=token,
                start=start,
                end=end,
                confidence=confidence,
                speech_confidence=confidence,
            )
        )
        start = end
    return ProviderResult(
        provider_name="test",
        provider_version="v1",
        words=normalized,
        segments=[],
        metadata={},
    )


def test_mispronunciation_counts_and_flags_yellow() -> None:
    tokens = CANONICAL_MANTRA_TEXT.split()
    tokens[0] = "hurry"
    outcome = score_provider_result(build_result(tokens), playback_available=True)

    assert outcome.final_count == 1
    assert outcome.yellow_flag_count == 1
    assert outcome.red_flag_count == 0
    assert outcome.gray_flag_count == 0
    assert outcome.flagged_mantras[0].flag_color == "yellow"
    assert outcome.flagged_mantras[0].counted is True


def test_missing_word_becomes_red_and_not_counted() -> None:
    tokens = CANONICAL_MANTRA_TEXT.split()
    tokens.pop(3)
    outcome = score_provider_result(build_result(tokens), playback_available=False)

    assert outcome.final_count == 0
    assert outcome.red_flag_count == 1
    assert outcome.flagged_mantras[0].flag_color == "red"
    assert outcome.flagged_mantras[0].counted is False


def test_interruption_token_becomes_gray() -> None:
    tokens = CANONICAL_MANTRA_TEXT.split()
    tokens.insert(5, "cough")
    tokens.pop(6)
    outcome = score_provider_result(build_result(tokens), playback_available=False)

    assert outcome.final_count == 0
    assert outcome.gray_flag_count == 1
    assert outcome.flagged_mantras[0].flag_color == "gray"


def test_ram_variant_is_valid() -> None:
    tokens = CANONICAL_MANTRA_TEXT.split()
    tokens[9] = "ram"
    tokens[11] = "ram"
    tokens[12] = "ram"
    tokens[13] = "ram"
    outcome = score_provider_result(build_result(tokens), playback_available=True)

    assert outcome.final_count == 1
    assert outcome.yellow_flag_count == 0
    assert outcome.red_flag_count == 0
    assert outcome.gray_flag_count == 0
