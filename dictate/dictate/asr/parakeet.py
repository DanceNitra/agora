"""Parakeet TDT 0.6B v3 ASR engine via sherpa-onnx."""

from __future__ import annotations

import logging
import time

import numpy as np

from .base import ASREngine, TranscriptionResult
from .models import model_paths

logger = logging.getLogger(__name__)


class ParakeetEngine(ASREngine):
    """Offline transducer recognizer for Parakeet TDT 0.6B v3."""

    def __init__(
        self,
        num_threads: int = 0,
        provider: str = "cpu",
        language: str | None = None,
    ) -> None:
        self.num_threads = num_threads
        self.provider = provider
        self.language = language
        self._recognizer = None
        self._load_seconds = 0.0

    def load(self) -> None:
        """Load the model into memory."""
        import sherpa_onnx

        paths = model_paths()
        start = time.perf_counter()
        self._recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(paths.encoder),
            decoder=str(paths.decoder),
            joiner=str(paths.joiner),
            tokens=str(paths.tokens),
            num_threads=self.num_threads or 1,
            sample_rate=16000,
            feature_dim=80,
            provider=self.provider,
            model_type="nemo_transducer",
        )
        self._load_seconds = time.perf_counter() - start
        logger.info("Loaded Parakeet model in %.2f s", self._load_seconds)

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio and return the result."""
        if self._recognizer is None:
            self.load()

        if audio.ndim != 1:
            raise ValueError(f"Expected 1-D audio, got shape {audio.shape}")
        if audio.size == 0:
            return TranscriptionResult(
                text="",
                duration_seconds=0.0,
                load_seconds=self._load_seconds,
                transcribe_seconds=0.0,
            )

        stream = self._recognizer.create_stream()
        stream.accept_waveform(sample_rate, audio.astype(np.float32))

        start = time.perf_counter()
        self._recognizer.decode_stream(stream)
        transcribe_seconds = time.perf_counter() - start

        text = stream.result.text.strip()
        duration = len(audio) / sample_rate
        return TranscriptionResult(
            text=text,
            duration_seconds=duration,
            load_seconds=self._load_seconds,
            transcribe_seconds=transcribe_seconds,
        )
