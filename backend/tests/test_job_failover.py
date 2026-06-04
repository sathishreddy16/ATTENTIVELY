from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db import Base
from app.enums import RetentionChoice
from app.models import AnalysisJob, SessionRecord
from app.services.analysis.providers.base import SpeechProviderError
from app.services.analysis.types import NormalizedWord, ProviderResult
from app.services.jobs import process_job


class FakeStorage:
    def __init__(self, path: Path) -> None:
        self.path = path

    def open_path(self, stored_path: str) -> Path:
        return Path(stored_path)

    def delete(self, stored_path: str) -> None:
        pass


class ExplodingProvider:
    name = "deepgram"
    version = "broken"

    def transcribe(self, audio_path: Path) -> ProviderResult:
        raise SpeechProviderError("quota hit")


class FallbackProvider:
    name = "groq"
    version = "whisper-large-v3-turbo"

    def transcribe(self, audio_path: Path) -> ProviderResult:
        tokens = "hare krishna hare krishna krishna krishna hare hare hare rama hare rama rama rama hare hare".split()
        words = []
        start = 0.0
        for token in tokens:
            end = start + 0.4
            words.append(NormalizedWord(text=token, raw_text=token, start=start, end=end, confidence=0.9))
            start = end
        return ProviderResult(provider_name=self.name, provider_version=self.version, words=words)


def test_job_uses_fallback_provider_when_primary_fails() -> None:
    with TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        audio_path = Path(temp_dir) / "session.wav"
        audio_path.write_bytes(b"fake")

        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(bind=engine)

        settings = Settings(
            database_url=f"sqlite:///{db_path}",
            upload_dir=Path(temp_dir),
            primary_speech_provider="deepgram",
        )

        with SessionLocal() as db:
            session_record = SessionRecord(
                device_id="device-1",
                started_at=datetime.now(timezone.utc),
                retention_choice=RetentionChoice.delete.value,
                original_filename="session.wav",
                upload_path=str(audio_path),
            )
            db.add(session_record)
            db.commit()
            db.refresh(session_record)

            job = AnalysisJob(session_id=session_record.id)
            db.add(job)
            db.commit()
            db.refresh(job)

            with patch("app.services.jobs.build_primary_provider", return_value=ExplodingProvider()):
                with patch("app.services.jobs.build_fallback_provider", return_value=FallbackProvider()):
                    processed = process_job(db, settings, FakeStorage(audio_path), job)

            assert processed.provider_selected == "groq"
            assert session_record.analysis_provider == "groq"
            assert session_record.final_count == 1
        
        engine.dispose()
