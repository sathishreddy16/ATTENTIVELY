from __future__ import annotations

from pathlib import Path
import math

import httpx

from app.config import Settings
from app.services.analysis.providers.base import SpeechProvider, SpeechProviderError
from app.services.analysis.types import NormalizedWord, ProviderResult, TranscriptSegment


class GroqProvider(SpeechProvider):
    name = "groq"

    def __init__(self, settings: Settings, model: str | None = None) -> None:
        self.settings = settings
        self.version = model or settings.groq_primary_model

    def transcribe(self, audio_path: Path) -> ProviderResult:
        if not self.settings.groq_api_key:
            raise SpeechProviderError("Groq API key is not configured.")

        with audio_path.open("rb") as audio_file:
            files = {"file": (audio_path.name, audio_file, "audio/wav")}
            data = {
                "model": self.version,
                "response_format": "verbose_json",
                "timestamp_granularities[]": ["word", "segment"],
                "language": "en",
                "prompt": "hare krishna hare krishna krishna krishna hare hare hare rama hare rama rama rama hare hare",
                "temperature": 0.0,
            }
            response = httpx.post(
                f"{self.settings.groq_base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.settings.groq_api_key}"},
                data=data,
                files=files,
                timeout=120.0,
            )

        if response.status_code >= 400:
            raise SpeechProviderError(f"Groq failed: {response.status_code} {response.text}")

        payload = response.json()
        words = [
            NormalizedWord(
                text=item.get("word", "").strip().lower(),
                raw_text=item.get("word", ""),
                start=float(item["start"]),
                end=float(item["end"]),
                confidence=item.get("probability"),
                speech_confidence=item.get("probability"),
            )
            for item in payload.get("words", [])
        ]
        segments = [
            TranscriptSegment(
                text=item.get("text", "").strip().lower(),
                start=float(item["start"]),
                end=float(item["end"]),
                confidence=max(0.0, min(1.0, math.exp(item.get("avg_logprob", 0.0)))),
                words=[],
            )
            for item in payload.get("segments", [])
        ]
        return ProviderResult(
            provider_name=self.name,
            provider_version=self.version,
            words=words,
            segments=segments,
            metadata={"language": payload.get("language")},
        )
