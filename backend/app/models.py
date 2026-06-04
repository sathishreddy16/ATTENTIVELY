from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.enums import JobStatus, RetentionChoice, SessionStatus


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    device_id: Mapped[str] = mapped_column(String(128), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=SessionStatus.created.value)
    analysis_status: Mapped[str] = mapped_column(String(32), default=SessionStatus.created.value)
    final_count: Mapped[int] = mapped_column(Integer, default=0)
    mala_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_total_after_session: Mapped[int] = mapped_column(Integer, default=0)
    retention_choice: Mapped[str] = mapped_column(String(16), default=RetentionChoice.delete.value)
    audio_kept: Mapped[bool] = mapped_column(Boolean, default=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    upload_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    analysis_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    analysis_provider_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    job_status: Mapped[str] = mapped_column(String(32), default=JobStatus.pending.value)
    job_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
    )

    report: Mapped[AnalysisReport | None] = relationship(back_populates="session", uselist=False)
    jobs: Mapped[list[AnalysisJob]] = relationship(back_populates="session", cascade="all, delete-orphan")
    chunks: Mapped[list[UploadPart]] = relationship(back_populates="session", cascade="all, delete-orphan")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.pending.value)
    provider_selected: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[SessionRecord] = relationship(back_populates="jobs")


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), unique=True)
    final_count: Mapped[int] = mapped_column(Integer, default=0)
    mala_count: Mapped[int] = mapped_column(Integer, default=0)
    yellow_flag_count: Mapped[int] = mapped_column(Integer, default=0)
    red_flag_count: Mapped[int] = mapped_column(Integer, default=0)
    gray_flag_count: Mapped[int] = mapped_column(Integer, default=0)
    pronunciation_score: Mapped[float] = mapped_column(Float, default=0.0)
    summary_text: Mapped[str] = mapped_column(Text, default="")
    analysis_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    analysis_provider_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[SessionRecord] = relationship(back_populates="report")
    flagged_mantras: Mapped[list[FlaggedMantra]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
    )


class FlaggedMantra(Base):
    __tablename__ = "flagged_mantras"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_reports.id"), index=True)
    start_sec: Mapped[float] = mapped_column(Float)
    end_sec: Mapped[float] = mapped_column(Float)
    flag_color: Mapped[str] = mapped_column(String(16))
    issue_type: Mapped[str] = mapped_column(String(32))
    expected_text: Mapped[str] = mapped_column(Text)
    detected_text: Mapped[str] = mapped_column(Text)
    counted: Mapped[bool] = mapped_column(Boolean, default=False)
    playback_available: Mapped[bool] = mapped_column(Boolean, default=False)

    report: Mapped[AnalysisReport] = relationship(back_populates="flagged_mantras")


class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    device_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    profile_version: Mapped[str] = mapped_column(String(64), default="v1")
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    baseline_pace_wpm: Mapped[float] = mapped_column(Float, default=0.0)
    accepted_confidence_mean: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
    )


class UploadPart(Base):
    __tablename__ = "upload_parts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    stored_path: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[SessionRecord] = relationship(back_populates="chunks")
