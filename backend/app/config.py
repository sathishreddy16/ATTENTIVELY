from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Chanting Coach API"
    app_env: str = "development"
    database_url: str = "sqlite:///./backend.db"
    upload_dir: Path = Path("uploads")
    storage_backend: str = "local"
    public_base_url: str = "http://localhost:8000"

    primary_speech_provider: str = "deepgram"
    deepgram_api_key: str = ""
    deepgram_base_url: str = "https://api.deepgram.com/v1"
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_primary_model: str = "whisper-large-v3-turbo"
    groq_verification_model: str = "whisper-large-v3"

    qstash_url: str = "https://qstash.upstash.io/v2/publish"
    qstash_token: str = ""
    qstash_current_signing_key: str = ""
    qstash_next_signing_key: str = ""

    s3_bucket: str = ""
    s3_region: str = "auto"
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""

    max_chunk_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
    max_provider_retries: int = Field(default=2, ge=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
