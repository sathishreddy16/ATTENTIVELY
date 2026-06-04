from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db import get_db
from app.db import Base
from app.dependencies import get_storage, settings_dependency
from app.enums import RetentionChoice
from app.main import create_app
from app.services.analysis.types import NormalizedWord, ProviderResult
from app.services.storage import LocalAudioStorage


class StubProvider:
    name = "deepgram"
    version = "stub-v1"

    def transcribe(self, audio_path: Path) -> ProviderResult:
        tokens = "hare krishna hare krishna krishna krishna hare hare hare rama hare rama rama rama hare hare".split()
        words = []
        start = 0.0
        for token in tokens:
            end = start + 0.4
            words.append(
                NormalizedWord(
                    text=token,
                    raw_text=token,
                    start=start,
                    end=end,
                    confidence=0.9,
                    speech_confidence=0.9,
                )
            )
            start = end
        return ProviderResult(provider_name=self.name, provider_version=self.version, words=words)


def build_test_client() -> tuple[TestClient, Session, Settings]:
    temp_dir = TemporaryDirectory()
    db_path = Path(temp_dir.name) / "api-test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        upload_dir=Path(temp_dir.name) / "uploads",
        public_base_url="http://testserver",
        max_chunk_bytes=1024 * 1024,
    )
    storage = LocalAudioStorage(settings)
    app = create_app(settings)

    def override_db() -> Session:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    client.temp_dir = temp_dir  # type: ignore[attr-defined]
    client.engine = engine  # type: ignore[attr-defined]
    return client, SessionLocal(), settings


def test_full_upload_process_and_playback_url() -> None:
    client, db, _ = build_test_client()
    try:
        create_response = client.post(
            "/sessions",
            json={
                "device_id": "device-1",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "retention_choice": RetentionChoice.keep.value,
                "original_filename": "chant.m4a",
            },
        )
        assert create_response.status_code == 201
        session_id = create_response.json()["session_id"]

        init_response = client.post(
            f"/sessions/{session_id}/upload/init",
            json={"file_size_bytes": 10, "mime_type": "audio/mp4"},
        )
        assert init_response.status_code == 200

        chunk_response = client.put(
            f"/sessions/{session_id}/upload/chunks/0",
            files={"file": ("chunk.part", b"test-audio", "application/octet-stream")},
        )
        assert chunk_response.status_code == 200

        complete_response = client.post(
            f"/sessions/{session_id}/upload/complete",
            json={"ended_at": datetime.now(timezone.utc).isoformat()},
        )
        assert complete_response.status_code == 202
        job_id = complete_response.json()["job_id"]

        with patch("app.services.jobs.build_primary_provider", return_value=StubProvider()):
            process_response = client.post(f"/internal/jobs/{job_id}/process", json={"job_id": job_id})
        assert process_response.status_code == 200

        report_response = client.get(f"/sessions/{session_id}/report")
        assert report_response.status_code == 200
        body = report_response.json()
        assert body["final_count"] == 1
        assert body["audio_playback_url"] == f"http://testserver/sessions/{session_id}/audio"

        audio_response = client.get(f"/sessions/{session_id}/audio")
        assert audio_response.status_code == 200
    finally:
        db.close()
        client.engine.dispose()  # type: ignore[attr-defined]
        client.temp_dir.cleanup()  # type: ignore[attr-defined]


def test_chunk_limit_is_enforced() -> None:
    client, db, settings = build_test_client()
    try:
        create_response = client.post(
            "/sessions",
            json={
                "device_id": "device-2",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "retention_choice": RetentionChoice.delete.value,
            },
        )
        session_id = create_response.json()["session_id"]
        client.post(
            f"/sessions/{session_id}/upload/init",
            json={"file_size_bytes": settings.max_chunk_bytes + 1, "mime_type": "audio/mp4"},
        )
        oversized = b"x" * (settings.max_chunk_bytes + 1)
        chunk_response = client.put(
            f"/sessions/{session_id}/upload/chunks/0",
            files={"file": ("chunk.part", oversized, "application/octet-stream")},
        )
        assert chunk_response.status_code == 413
    finally:
        db.close()
        client.engine.dispose()  # type: ignore[attr-defined]
        client.temp_dir.cleanup()  # type: ignore[attr-defined]


def test_deleted_audio_sessions_do_not_expose_playback() -> None:
    client, db, _ = build_test_client()
    try:
        create_response = client.post(
            "/sessions",
            json={
                "device_id": "device-3",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "retention_choice": RetentionChoice.delete.value,
                "original_filename": "chant.m4a",
            },
        )
        session_id = create_response.json()["session_id"]
        client.post(
            f"/sessions/{session_id}/upload/init",
            json={"file_size_bytes": 10, "mime_type": "audio/mp4"},
        )
        client.put(
            f"/sessions/{session_id}/upload/chunks/0",
            files={"file": ("chunk.part", b"test-audio", "application/octet-stream")},
        )
        complete_response = client.post(
            f"/sessions/{session_id}/upload/complete",
            json={"ended_at": datetime.now(timezone.utc).isoformat()},
        )
        job_id = complete_response.json()["job_id"]

        with patch("app.services.jobs.build_primary_provider", return_value=StubProvider()):
            process_response = client.post(f"/internal/jobs/{job_id}/process", json={"job_id": job_id})
        assert process_response.status_code == 200

        report_response = client.get(f"/sessions/{session_id}/report")
        assert report_response.status_code == 200
        assert report_response.json()["audio_playback_url"] is None

        audio_response = client.get(f"/sessions/{session_id}/audio")
        assert audio_response.status_code == 404
    finally:
        db.close()
        client.engine.dispose()  # type: ignore[attr-defined]
        client.temp_dir.cleanup()  # type: ignore[attr-defined]
