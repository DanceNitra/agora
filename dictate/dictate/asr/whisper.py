"""faster-whisper ASR engine (CUDA, int8_float16 by default).

Whisper forces the language explicitly, which is why it is the only engine here. The
Parakeet engine this replaced auto-detected Slovak as Polish and wrote Polish
orthography, and no amount of post-processing recovers that.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

from .base import ASREngine, TranscriptionResult

logger = logging.getLogger(__name__)


def _register_cuda_dll_dirs() -> None:
    """Make cuBLAS/cuDNN DLLs from pip wheels visible to CTranslate2."""
    try:
        import site

        for site_dir in site.getsitepackages():
            nvidia_dir = Path(site_dir) / "nvidia"
            if not nvidia_dir.is_dir():
                continue
            for dll_dir in sorted(nvidia_dir.glob("*/bin")):
                try:
                    import os

                    os.add_dll_directory(str(dll_dir))
                    logger.debug("Added CUDA DLL dir: %s", dll_dir)
                except OSError:
                    pass
    except Exception:
        logger.debug("CUDA DLL dir registration failed", exc_info=True)


class WhisperEngine(ASREngine):
    """Offline faster-whisper engine with CUDA support and language forcing."""

    def __init__(
        self,
        model_name: str = "large-v3-turbo",
        device: str = "cuda",
        compute_type: str = "int8_float16",
        language: str | None = "sk",
        num_threads: int = 0,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.num_threads = num_threads
        self._model = None
        self._load_seconds = 0.0

    def _model_source(self) -> str:
        """Return the installed model directory, or the alias when nothing is installed.

        The installer downloads the weights into the app's own models directory, so a
        machine that never ran faster-whisper before still starts offline. Falling back
        to the alias keeps a development checkout working against the Hugging Face cache.
        """
        from .models import is_model_installed, model_dir

        if is_model_installed():
            return str(model_dir())
        logger.info("No installed weights; falling back to the alias %s", self.model_name)
        return self.model_name

    def load(self) -> None:
        """Load the model (downloads on first run)."""
        _register_cuda_dll_dirs()
        from faster_whisper import WhisperModel

        start = time.perf_counter()
        self._model = WhisperModel(
            self._model_source(),
            device=self.device,
            compute_type=self.compute_type,
        )
        self._load_seconds = time.perf_counter() - start
        logger.info(
            "Loaded whisper %s device=%s in %.2f s",
            self.model_name,
            self.device,
            self._load_seconds,
        )

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe 16 kHz float32 audio; language is forced when set."""
        if self._model is None:
            self.load()

        if audio.ndim != 1:
            raise ValueError(f"Expected 1-D audio, got shape {audio.shape}")
        duration = len(audio) / sample_rate
        if audio.size == 0 or duration < 0.1:
            return TranscriptionResult(
                text="",
                duration_seconds=duration,
                load_seconds=self._load_seconds,
                transcribe_seconds=0.0,
            )


        audio_16k = audio if sample_rate == 16000 else _resample(audio, sample_rate)

        start = time.perf_counter()
        segments, info = self._model.transcribe(
            audio_16k,
            language=language or self.language,
            beam_size=1,
            vad_filter=True,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        transcribe_seconds = time.perf_counter() - start

        logger.info(
            "Whisper: %.2fs audio in %.2fs (%.3f RTF), lang=%s prob=%.2f",
            duration,
            transcribe_seconds,
            transcribe_seconds / max(duration, 1e-9),
            info.language,
            info.language_probability,
        )
        return TranscriptionResult(
            text=text,
            duration_seconds=duration,
            load_seconds=self._load_seconds,
            transcribe_seconds=transcribe_seconds,
        )


def _resample(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    from ..audio.resample import resample

    return resample(audio, sample_rate, 16000)
