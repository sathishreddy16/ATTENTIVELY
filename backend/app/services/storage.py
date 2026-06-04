from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import boto3

from app.config import Settings


class AudioStorage(ABC):
    @abstractmethod
    def write_chunk(self, session_id: str, chunk_index: int, data: bytes) -> str:
        raise NotImplementedError

    @abstractmethod
    def assemble_chunks(self, session_id: str, chunk_paths: list[str], destination_name: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def open_path(self, stored_path: str) -> Path:
        raise NotImplementedError

    @abstractmethod
    def delete(self, stored_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_many(self, stored_paths: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_download_url(self, stored_path: str, public_base_url: str, session_id: str) -> str | None:
        raise NotImplementedError


class LocalAudioStorage(AudioStorage):
    def __init__(self, settings: Settings) -> None:
        self.root = settings.upload_dir.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def write_chunk(self, session_id: str, chunk_index: int, data: bytes) -> str:
        session_dir = self.root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        chunk_path = session_dir / f"chunk-{chunk_index:05d}.part"
        chunk_path.write_bytes(data)
        return str(chunk_path)

    def assemble_chunks(self, session_id: str, chunk_paths: list[str], destination_name: str) -> str:
        session_dir = self.root / session_id
        final_path = session_dir / destination_name
        with final_path.open("wb") as output:
            for chunk_path in chunk_paths:
                output.write(Path(chunk_path).read_bytes())
        return str(final_path)

    def open_path(self, stored_path: str) -> Path:
        return Path(stored_path)

    def delete(self, stored_path: str) -> None:
        path = Path(stored_path)
        if path.exists():
            path.unlink()

    def delete_many(self, stored_paths: list[str]) -> None:
        for stored_path in stored_paths:
            self.delete(stored_path)

    def get_download_url(self, stored_path: str, public_base_url: str, session_id: str) -> str | None:
        return f"{public_base_url.rstrip('/')}/sessions/{session_id}/audio"


class S3AudioStorage(AudioStorage):
    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )
        self.local_cache = settings.upload_dir.resolve()
        self.local_cache.mkdir(parents=True, exist_ok=True)

    def write_chunk(self, session_id: str, chunk_index: int, data: bytes) -> str:
        key = f"{session_id}/chunks/chunk-{chunk_index:05d}.part"
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    def assemble_chunks(self, session_id: str, chunk_paths: list[str], destination_name: str) -> str:
        combined = self.local_cache / session_id / destination_name
        combined.parent.mkdir(parents=True, exist_ok=True)
        with combined.open("wb") as output:
            for key in chunk_paths:
                response = self.client.get_object(Bucket=self.bucket, Key=key)
                output.write(response["Body"].read())
        final_key = f"{session_id}/{destination_name}"
        self.client.upload_file(str(combined), self.bucket, final_key)
        return final_key

    def open_path(self, stored_path: str) -> Path:
        local_path = self.local_cache / stored_path.replace("/", "_")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, stored_path, str(local_path))
        return local_path

    def delete(self, stored_path: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=stored_path)

    def delete_many(self, stored_paths: list[str]) -> None:
        if not stored_paths:
            return
        self.client.delete_objects(
            Bucket=self.bucket,
            Delete={"Objects": [{"Key": stored_path} for stored_path in stored_paths]},
        )

    def get_download_url(self, stored_path: str, public_base_url: str, session_id: str) -> str | None:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": stored_path},
            ExpiresIn=3600,
        )


def build_storage(settings: Settings) -> AudioStorage:
    if settings.storage_backend == "s3":
        return S3AudioStorage(settings)
    return LocalAudioStorage(settings)
