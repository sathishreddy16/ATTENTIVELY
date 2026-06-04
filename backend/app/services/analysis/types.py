from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class NormalizedWord:
    text: str
    start: float
    end: float
    confidence: float | None = None
    speech_confidence: float | None = None
    raw_text: str | None = None


@dataclass(slots=True)
class TranscriptSegment:
    text: str
    start: float
    end: float
    confidence: float | None = None
    words: list[NormalizedWord] = field(default_factory=list)


@dataclass(slots=True)
class ProviderResult:
    provider_name: str
    provider_version: str
    words: list[NormalizedWord]
    segments: list[TranscriptSegment] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class FlaggedMantraOutcome:
    start_sec: float
    end_sec: float
    flag_color: str
    issue_type: str
    expected_text: str
    detected_text: str
    counted: bool
    playback_available: bool


@dataclass(slots=True)
class AnalysisOutcome:
    final_count: int
    mala_count: int
    yellow_flag_count: int
    red_flag_count: int
    gray_flag_count: int
    pronunciation_score: float
    summary_text: str
    flagged_mantras: list[FlaggedMantraOutcome]
    provider_name: str
    provider_version: str
