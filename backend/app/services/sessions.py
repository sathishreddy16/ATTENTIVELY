from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import JobStatus, SessionStatus
from app.models import SessionRecord
from app.schemas import DailyProgressResponse, SessionCreate


def create_session(db: Session, payload: SessionCreate) -> SessionRecord:
    session = SessionRecord(
        device_id=payload.device_id,
        started_at=payload.started_at,
        retention_choice=payload.retention_choice.value,
        original_filename=payload.original_filename,
        status=SessionStatus.created.value,
        analysis_status=SessionStatus.created.value,
        job_status=JobStatus.pending.value,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: str) -> SessionRecord | None:
    return db.get(SessionRecord, session_id)


def build_daily_progress(db: Session, target_date: date) -> DailyProgressResponse:
    rows = db.execute(
        select(SessionRecord.id, SessionRecord.final_count)
        .where(func.date(SessionRecord.started_at) == target_date.isoformat())
        .where(SessionRecord.status == SessionStatus.completed.value)
    ).all()

    total_count = sum(row.final_count for row in rows)
    total_malas = total_count // 108
    return DailyProgressResponse(
        date=target_date.isoformat(),
        total_count=total_count,
        total_malas=total_malas,
        remaining_to_sixteen=max(16 - total_malas, 0),
        completed_session_ids=[row.id for row in rows],
    )
