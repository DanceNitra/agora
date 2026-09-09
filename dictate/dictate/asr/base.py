"""ASR engine base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class TranscriptionResult:
    """Result of a transcription."""

    text: str
    duration_seconds: float
    load_seconds: float
    transcribe_seconds: float

    @property
    def rtf(self) -> float:
        """Real-time factor: transcribe time divided by audio duration."""
        if self.duration_seconds <= 0:
            return 0.0
        return self.transcribe_seconds / self.duration_seconds


class ASREngine(ABC):
    """Abstract base class for speech-to-text engines."""

    @abstractmethod
    def load(self) -> None:
        """Load the model into memory."""

    @abstractmethod
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio and return the result."""
