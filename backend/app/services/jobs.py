import logging

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.enums import JobStatus, SessionStatus
from app.models import AnalysisJob, AnalysisReport, FlaggedMantra, SessionRecord, VoiceProfile
from app.services.analysis.normalizer import normalize_audio
from app.services.analysis.providers.base import SpeechProviderError
from app.services.analysis.scorer import score_provider_result
from app.services.providers import build_fallback_provider, build_primary_provider
from app.services.qstash import publish_job
from app.services.storage import AudioStorage

logger = logging.getLogger(__name__)


def create_job(db: Session, session_record: SessionRecord) -> AnalysisJob:
    job = AnalysisJob(session_id=session_record.id, status=JobStatus.pending.value)
    session_record.job_status = JobStatus.pending.value
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def enqueue_job(settings: Settings, job: AnalysisJob) -> None:
    publish_job(settings, job.id)


def process_job(db: Session, settings: Settings, storage: AudioStorage, job: AnalysisJob) -> AnalysisJob:
    session_record = db.get(SessionRecord, job.session_id)
    if session_record is None or not session_record.upload_path:
        logger.error("Job %s failed: Session record not found or upload path missing.", job.id)
        raise ValueError("Session upload is not ready for analysis.")

    logger.info("Starting analysis job %s for session %s", job.id, session_record.id)
    job.status = JobStatus.processing.value
    job.started_at = datetime.now(timezone.utc)
    job.retry_count += 1
    session_record.job_status = JobStatus.processing.value
    session_record.job_attempt_count += 1
    db.commit()

    primary = build_primary_provider(settings)
    fallback = build_fallback_provider(settings)

    logger.info("Downloading/opening audio from storage: %s", session_record.upload_path)
    raw_audio_path = storage.open_path(session_record.upload_path)

    logger.info("Normalizing audio for job %s", job.id)
    audio_path = normalize_audio(raw_audio_path)

    try:
        try:
            provider_used = primary
            logger.info("Transcribing with primary provider (%s) for job %s", primary.name, job.id)
            result = primary.transcribe(audio_path)
        except SpeechProviderError as primary_error:
            logger.warning("Primary provider failed for job %s: %s. Trying fallback.", job.id, primary_error)
            job.last_error = str(primary_error)
            provider_used = fallback
            logger.info("Transcribing with fallback provider (%s) for job %s", fallback.name, job.id)
            result = fallback.transcribe(audio_path)

        logger.info("Scoring result for job %s", job.id)
        outcome = score_provider_result(result, playback_available=session_record.retention_choice == "keep")

        session_record.analysis_provider = outcome.provider_name
        session_record.analysis_provider_version = outcome.provider_version
        session_record.final_count = outcome.final_count
        session_record.mala_count = outcome.mala_count
        session_record.status = SessionStatus.completed.value
        session_record.analysis_status = SessionStatus.completed.value
        session_record.job_status = JobStatus.completed.value
        session_record.audio_kept = session_record.retention_choice == "keep"

        logger.info("Computing daily total for session %s", session_record.id)
        session_record.daily_total_after_session = _compute_daily_total(db, session_record)

        report = session_record.report or AnalysisReport(session_id=session_record.id)
        report.final_count = outcome.final_count
        report.mala_count = outcome.mala_count
        report.yellow_flag_count = outcome.yellow_flag_count
        report.red_flag_count = outcome.red_flag_count
        report.gray_flag_count = outcome.gray_flag_count
        report.pronunciation_score = outcome.pronunciation_score
        report.summary_text = outcome.summary_text
        report.analysis_provider = outcome.provider_name
        report.analysis_provider_version = outcome.provider_version

        report.flagged_mantras.clear()
        for flagged in outcome.flagged_mantras:
            report.flagged_mantras.append(
                FlaggedMantra(
                    start_sec=flagged.start_sec,
                    end_sec=flagged.end_sec,
                    flag_color=flagged.flag_color,
                    issue_type=flagged.issue_type,
                    expected_text=flagged.expected_text,
                    detected_text=flagged.detected_text,
                    counted=flagged.counted,
                    playback_available=flagged.playback_available,
                )
            )

        if session_record.report is None:
            db.add(report)

        logger.info("Updating voice profile for device %s", session_record.device_id)
        _update_voice_profile(db, session_record.device_id, outcome.pronunciation_score)

        job.status = JobStatus.completed.value
        job.provider_selected = provider_used.name
        job.finished_at = datetime.now(timezone.utc)

        if session_record.retention_choice != "keep":
            logger.info("Deleting audio as per retention choice: %s", session_record.upload_path)
            storage.delete(session_record.upload_path)
            session_record.upload_path = None

        db.commit()
        logger.info("Analysis job %s COMPLETED", job.id)
        db.refresh(job)
        if audio_path != raw_audio_path and audio_path.exists():
            audio_path.unlink(missing_ok=True)
        return job
    except Exception as error:
        logger.exception("Analysis job %s FAILED with error: %s", job.id, error)
        job.status = JobStatus.failed.value
        job.last_error = str(error)
        job.finished_at = datetime.now(timezone.utc)
        session_record.status = SessionStatus.failed.value
        session_record.analysis_status = SessionStatus.failed.value
        session_record.job_status = JobStatus.failed.value
        db.commit()
        if audio_path != raw_audio_path and audio_path.exists():
            audio_path.unlink(missing_ok=True)
        raise


def _update_voice_profile(db: Session, device_id: str, pronunciation_score: float) -> None:
    profile = db.get(VoiceProfile, device_id)
    if profile is None:
        profile = VoiceProfile(
            device_id=device_id,
            sample_count=1,
            accepted_confidence_mean=pronunciation_score / 100,
            baseline_pace_wpm=0.0,
        )
        db.add(profile)
        return

    profile.sample_count += 1
    profile.accepted_confidence_mean = (
        (profile.accepted_confidence_mean * (profile.sample_count - 1)) + (pronunciation_score / 100)
    ) / profile.sample_count


def _compute_daily_total(db: Session, session_record: SessionRecord) -> int:
    if session_record.started_at is None:
        return session_record.final_count
    same_day_total = db.execute(
        select(func.coalesce(func.sum(SessionRecord.final_count), 0))
        .where(func.date(SessionRecord.started_at) == session_record.started_at.date())
        .where(SessionRecord.id != session_record.id)
        .where(SessionRecord.status == SessionStatus.completed.value)
    ).scalar_one()
    return int(same_day_total) + session_record.final_count
