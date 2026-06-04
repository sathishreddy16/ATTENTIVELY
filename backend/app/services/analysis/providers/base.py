from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.services.analysis.types import ProviderResult


class SpeechProviderError(RuntimeError):
    """Raised when a provider call fails."""


class SpeechProvider(ABC):
    name: str
    version: str

    @abstractmethod
    def transcribe(self, audio_path: Path) -> ProviderResult:
        raise NotImplementedError
