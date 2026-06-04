from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import SessionStatus
from app.models import SessionRecord, UploadPart
from app.services.storage import AudioStorage


def init_upload(session_record: SessionRecord) -> SessionRecord:
    session_record.status = SessionStatus.upload_initialized.value
    session_record.analysis_status = SessionStatus.upload_initialized.value
    return session_record


def save_chunk(
    db: Session,
    session_record: SessionRecord,
    storage: AudioStorage,
    chunk_index: int,
    data: bytes,
) -> UploadPart:
    stored_path = storage.write_chunk(session_record.id, chunk_index, data)

    existing = db.execute(
        select(UploadPart).where(UploadPart.session_id == session_record.id).where(UploadPart.chunk_index == chunk_index)
    ).scalar_one_or_none()
    if existing is None:
        existing = UploadPart(
            session_id=session_record.id,
            chunk_index=chunk_index,
            size_bytes=len(data),
            stored_path=stored_path,
        )
        db.add(existing)
    else:
        existing.size_bytes = len(data)
        existing.stored_path = stored_path

    session_record.status = SessionStatus.uploading.value
    session_record.analysis_status = SessionStatus.uploading.value
    db.commit()
    db.refresh(existing)
    return existing


def complete_upload(
    db: Session,
    session_record: SessionRecord,
    storage: AudioStorage,
    destination_name: str,
) -> str:
    parts = db.execute(
        select(UploadPart).where(UploadPart.session_id == session_record.id).order_by(UploadPart.chunk_index.asc())
    ).scalars().all()
    upload_path = storage.assemble_chunks(
        session_record.id,
        [item.stored_path for item in parts],
        destination_name,
    )
    session_record.upload_path = upload_path
    session_record.status = SessionStatus.analysis_pending.value
    session_record.analysis_status = SessionStatus.analysis_pending.value
    storage.delete_many([item.stored_path for item in parts])
    for part in parts:
        db.delete(part)
    db.commit()
    return upload_path
