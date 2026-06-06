from __future__ import annotations

from pathlib import Path

import httpx

from app.config import Settings
from app.services.analysis.providers.base import SpeechProvider, SpeechProviderError
from app.services.analysis.types import NormalizedWord, ProviderResult, TranscriptSegment


class DeepgramProvider(SpeechProvider):
    name = "deepgram"
    version = "nova-2"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def transcribe(self, audio_path: Path) -> ProviderResult:
        if not self.settings.deepgram_api_key:
            raise SpeechProviderError("Deepgram API key is not configured.")

        with audio_path.open("rb") as audio_file:
            response = httpx.post(
                f"{self.settings.deepgram_base_url}/listen",
                params={
                    "model": self.version,
                    "language": "hi",
                    "smart_format": "false",
                    "utterances": "true",
                    "punctuate": "false",
                    "dictation": "true",
                },
                headers={"Authorization": f"Token {self.settings.deepgram_api_key}"},
                content=audio_file.read(),
                timeout=120.0,
            )

        if response.status_code >= 400:
            raise SpeechProviderError(f"Deepgram failed: {response.status_code} {response.text}")

        payload = response.json()
        channel = payload["results"]["channels"][0]
        alternative = channel["alternatives"][0]

        words = [
            NormalizedWord(
                text=(item.get("punctuated_word") or item.get("word", "")).strip().lower(),
                raw_text=item.get("word", ""),
                start=float(item["start"]),
                end=float(item["end"]),
                confidence=item.get("confidence"),
                speech_confidence=item.get("confidence"),
            )
            for item in alternative.get("words", [])
        ]

        segments = []
        for utterance in payload["results"].get("utterances", []):
            utterance_words = [
                NormalizedWord(
                    text=(item.get("punctuated_word") or item.get("word", "")).strip().lower(),
                    raw_text=item.get("word", ""),
                    start=float(item["start"]),
                    end=float(item["end"]),
                    confidence=item.get("confidence"),
                    speech_confidence=item.get("confidence"),
                )
                for item in utterance.get("words", [])
            ]
            segments.append(
                TranscriptSegment(
                    text=utterance.get("transcript", "").strip().lower(),
                    start=float(utterance["start"]),
                    end=float(utterance["end"]),
                    confidence=utterance.get("confidence"),
                    words=utterance_words,
                )
            )

        return ProviderResult(
            provider_name=self.name,
            provider_version=self.version,
            words=words,
            segments=segments,
            metadata={"request_id": payload.get("metadata", {}).get("request_id")},
        )
