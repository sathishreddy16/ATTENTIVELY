from __future__ import annotations

from app.config import Settings
from app.services.analysis.providers.base import SpeechProvider
from app.services.analysis.providers.deepgram import DeepgramProvider
from app.services.analysis.providers.groq import GroqProvider


def build_primary_provider(settings: Settings) -> SpeechProvider:
    if settings.primary_speech_provider == "groq":
        return GroqProvider(settings, settings.groq_primary_model)
    return DeepgramProvider(settings)


def build_fallback_provider(settings: Settings) -> SpeechProvider:
    return GroqProvider(settings, settings.groq_primary_model)
