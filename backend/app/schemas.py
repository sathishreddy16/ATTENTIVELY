from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.enums import FlagColor, IssueType, RetentionChoice


class SessionCreate(BaseModel):
    device_id: str
    started_at: datetime
    retention_choice: RetentionChoice = RetentionChoice.delete
    original_filename: str | None = None


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str


class ErrorResponse(BaseModel):
    detail: str


class UploadInitRequest(BaseModel):
    file_size_bytes: int = Field(ge=1)
    mime_type: str | None = None


class UploadInitResponse(BaseModel):
    session_id: str
    max_chunk_bytes: int
    status: str


class UploadChunkResponse(BaseModel):
    session_id: str
    chunk_index: int
    size_bytes: int
    status: str


class CompleteUploadRequest(BaseModel):
    ended_at: datetime


class CompleteUploadResponse(BaseModel):
    job_id: str
    session_id: str
    status: str


class FlaggedMantraResponse(BaseModel):
    id: str
    start_sec: float
    end_sec: float
    flag_color: FlagColor
    issue_type: IssueType
    expected_text: str
    detected_text: str
    counted: bool
    playback_available: bool


class SessionReportResponse(BaseModel):
    session_id: str
    status: str
    analysis_provider: str | None
    analysis_provider_version: str | None
    audio_playback_url: str | None
    final_count: int
    mala_count: int
    yellow_flag_count: int
    red_flag_count: int
    gray_flag_count: int
    pronunciation_score: float
    summary_text: str
    flagged_mantras: list[FlaggedMantraResponse]


class DailyProgressResponse(BaseModel):
    date: str
    total_count: int
    total_malas: int
    remaining_to_sixteen: int
    completed_session_ids: list[str]


class JobProcessResponse(BaseModel):
    job_id: str
    session_id: str
    status: str
    provider_selected: str | None = None


class ProviderWordSchema(BaseModel):
    text: str
    start: float
    end: float
    confidence: float | None = None
    speech_confidence: float | None = None


class ProviderSegmentSchema(BaseModel):
    text: str
    start: float
    end: float
    confidence: float | None = None
    words: list[ProviderWordSchema] = Field(default_factory=list)
