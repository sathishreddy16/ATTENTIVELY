from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.dependencies import get_storage, settings_dependency
from app.models import AnalysisJob
from app.schemas import JobProcessResponse
from app.services.jobs import process_job
from app.services.qstash import verify_qstash_signature
from app.services.storage import AudioStorage


router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/jobs/{job_id}/process", response_model=JobProcessResponse)
async def process_job_route(
    job_id: str,
    request: Request,
    upstash_signature: str | None = Header(default=None, alias="Upstash-Signature"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dependency),
    storage: AudioStorage = Depends(get_storage),
) -> JobProcessResponse:
    raw_body = await request.body()
    if not verify_qstash_signature(raw_body, upstash_signature, str(request.url), settings):
        raise HTTPException(status_code=401, detail="Invalid QStash signature")

    job = db.get(AnalysisJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    processed = process_job(db, settings, storage, job)
    return JobProcessResponse(
        job_id=processed.id,
        session_id=processed.session_id,
        status=processed.status,
        provider_selected=processed.provider_selected,
    )
