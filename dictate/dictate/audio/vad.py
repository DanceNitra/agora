"""Silero VAD via sherpa-onnx: speech detection and silence trimming.

The VAD runs at 16 kHz on a resampled copy of the audio; trim() returns
16 kHz mono audio containing only the speech region plus padding.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from ..asr.models import vad_model_path
from .resample import resample

logger = logging.getLogger(__name__)

VAD_SAMPLE_RATE = 16000


@dataclass
class SpeechRegion:
    """Speech bounds in 16 kHz samples."""

    start: int
    end: int


class SileroVAD:
    """Offline VAD wrapper for trimming leading/trailing silence."""

    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_duration: float = 0.25,
        num_threads: int = 1,
    ) -> None:
        self.threshold = threshold
        self.min_speech_duration = min_speech_duration
        self.num_threads = num_threads
        self._model = None

    def _load(self):
        """Load the VAD model once."""
        import sherpa_onnx

        if self._model is None:
            config = sherpa_onnx.SileroVadModelConfig(
                model=str(vad_model_path()),
                threshold=self.threshold,
                min_speech_duration=self.min_speech_duration,
            )
            self._model = sherpa_onnx.VadModel.create(
                sherpa_onnx.VadModelConfig(
                    silero_vad=config,
                    sample_rate=VAD_SAMPLE_RATE,
                    num_threads=self.num_threads,
                    provider="cpu",
                )
            )
        return self._model

    def speech_region(self, audio_16k: np.ndarray) -> SpeechRegion | None:
        """Return the first/last speech window bounds, or None if silent.

        ``audio_16k`` must be 1-D float32 at 16 kHz. Windows of
        ``window_size()`` samples are scanned; the returned region spans
        the first window containing speech to the end of the last one.
        """
        model = self._load()
        model.reset()
        window = model.window_size()
        total = audio_16k.size
        if total < window:
            return None
        first: int | None = None
        last: int | None = None
        for start in range(0, total - window + 1, window):
            chunk = audio_16k[start : start + window]
            if model.is_speech(chunk.tolist()):
                if first is None:
                    first = start
                last = start
        if first is None:
            return None
        return SpeechRegion(start=first, end=last + window)

    def has_speech(self, audio: np.ndarray, sample_rate: int) -> bool:
        """Return True if any speech is detected in ``audio``."""
        audio_16k = resample(audio, sample_rate, VAD_SAMPLE_RATE)
        return self.speech_region(audio_16k) is not None

    def trim(
        self,
        audio: np.ndarray,
        sample_rate: int,
        preroll_ms: int = 250,
        tail_pad_ms: int = 250,
    ) -> np.ndarray:
        """Trim leading/trailing silence and return 16 kHz mono audio.

        Keeps ``preroll_ms`` of audio before the first speech window and
        ``tail_pad_ms`` after the last one. Returns an empty array when
        no speech is detected.
        """
        audio_16k = resample(audio, sample_rate, VAD_SAMPLE_RATE)
        region = self.speech_region(audio_16k)
        if region is None:
            return np.zeros(0, dtype=np.float32)
        preroll = int(preroll_ms / 1000 * VAD_SAMPLE_RATE)
        tail = int(tail_pad_ms / 1000 * VAD_SAMPLE_RATE)
        start = max(0, region.start - preroll)
        end = min(audio_16k.size, region.end + tail)
        return audio_16k[start:end]


