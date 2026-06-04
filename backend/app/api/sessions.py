from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.dependencies import get_storage, settings_dependency
from app.schemas import (
    CompleteUploadRequest,
    CompleteUploadResponse,
    DailyProgressResponse,
    ErrorResponse,
    SessionCreate,
    SessionCreateResponse,
    SessionReportResponse,
    UploadChunkResponse,
    UploadInitRequest,
    UploadInitResponse,
)
from app.services.jobs import create_job, enqueue_job
from app.services.sessions import build_daily_progress, create_session, get_session
from app.services.storage import AudioStorage
from app.services.uploads import complete_upload, init_upload, save_chunk


router = APIRouter(prefix="", tags=["sessions"])


@router.post("/sessions", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
def create_session_route(payload: SessionCreate, db: Session = Depends(get_db)) -> SessionCreateResponse:
    session_record = create_session(db, payload)
    return SessionCreateResponse(session_id=session_record.id, status=session_record.status)


@router.post("/sessions/{session_id}/upload/init", response_model=UploadInitResponse)
def init_upload_route(
    session_id: str,
    payload: UploadInitRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dependency),
) -> UploadInitResponse:
    session_record = get_session(db, session_id)
    if session_record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    init_upload(session_record)
    db.commit()
    return UploadInitResponse(
        session_id=session_record.id,
        max_chunk_bytes=settings.max_chunk_bytes,
        status=session_record.status,
    )


@router.put("/sessions/{session_id}/upload/chunks/{chunk_index}", response_model=UploadChunkResponse)
def upload_chunk_route(
    session_id: str,
    chunk_index: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: AudioStorage = Depends(get_storage),
    settings: Settings = Depends(settings_dependency),
) -> UploadChunkResponse:
    session_record = get_session(db, session_id)
    if session_record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    data = file.file.read()
    if len(data) > settings.max_chunk_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Chunk exceeds max size of {settings.max_chunk_bytes} bytes",
        )
    saved = save_chunk(db, session_record, storage, chunk_index, data)
    return UploadChunkResponse(
        session_id=session_record.id,
        chunk_index=saved.chunk_index,
        size_bytes=saved.size_bytes,
        status=session_record.status,
    )


@router.post("/sessions/{session_id}/upload/complete", status_code=status.HTTP_202_ACCEPTED)
def complete_upload_route(
    session_id: str,
    payload: CompleteUploadRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dependency),
    storage: AudioStorage = Depends(get_storage),
) -> CompleteUploadResponse:
    session_record = get_session(db, session_id)
    if session_record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session_record.ended_at = payload.ended_at
    destination_name = Path(session_record.original_filename or "session.m4a").name
    complete_upload(db, session_record, storage, destination_name)
    job = create_job(db, session_record)
    try:
        enqueue_job(settings, job)
        return CompleteUploadResponse(job_id=job.id, session_id=session_record.id, status="queued")
    except Exception as e:
        job.status = "enqueue_failed"
        job.last_error = str(e)
        session_record.job_status = "enqueue_failed"
        db.commit()
        return CompleteUploadResponse(job_id=job.id, session_id=session_record.id, status="enqueue_failed")


@router.get("/sessions/{session_id}/report", response_model=SessionReportResponse)
def session_report_route(
    session_id: str,
    db: Session = Depends(get_db),
    storage: AudioStorage = Depends(get_storage),
    settings: Settings = Depends(settings_dependency),
) -> SessionReportResponse:
    session_record = get_session(db, session_id)
    if session_record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    report = session_record.report
    flagged = []
    if report:
        flagged = [
            {
                "id": item.id,
                "start_sec": item.start_sec,
                "end_sec": item.end_sec,
                "flag_color": item.flag_color,
                "issue_type": item.issue_type,
                "expected_text": item.expected_text,
                "detected_text": item.detected_text,
                "counted": item.counted,
                "playback_available": item.playback_available,
            }
            for item in report.flagged_mantras
        ]

    return SessionReportResponse(
        session_id=session_record.id,
        status=session_record.analysis_status,
        analysis_provider=session_record.analysis_provider,
        analysis_provider_version=session_record.analysis_provider_version,
        audio_playback_url=(
            storage.get_download_url(session_record.upload_path, settings.public_base_url, session_record.id)
            if session_record.audio_kept and session_record.upload_path
            else None
        ),
        final_count=session_record.final_count,
        mala_count=session_record.mala_count,
        yellow_flag_count=report.yellow_flag_count if report else 0,
        red_flag_count=report.red_flag_count if report else 0,
        gray_flag_count=report.gray_flag_count if report else 0,
        pronunciation_score=report.pronunciation_score if report else 0,
        summary_text=report.summary_text if report else "Analysis pending.",
        flagged_mantras=flagged,
    )


@router.get(
    "/sessions/{session_id}/audio",
    response_model=None,
    responses={404: {"model": ErrorResponse}},
)
def session_audio_route(
    session_id: str,
    db: Session = Depends(get_db),
    storage: AudioStorage = Depends(get_storage),
) -> FileResponse | RedirectResponse:
    session_record = get_session(db, session_id)
    if session_record is None or not session_record.audio_kept or not session_record.upload_path:
        raise HTTPException(status_code=404, detail="Retained audio not found")

    download_url = storage.get_download_url(session_record.upload_path, "", session_record.id)
    if download_url and download_url.startswith("http"):
        return RedirectResponse(download_url)

    audio_path = storage.open_path(session_record.upload_path)
    return FileResponse(audio_path)


@router.get("/daily-progress", response_model=DailyProgressResponse)
def daily_progress_route(
    target_date: date = Query(alias="date"),
    db: Session = Depends(get_db),
) -> DailyProgressResponse:
    return build_daily_progress(db, target_date)
