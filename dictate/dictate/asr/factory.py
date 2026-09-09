"""Build the configured ASR engine."""

from __future__ import annotations

from ..config import DictateConfig
from .base import ASREngine
from .parakeet import ParakeetEngine


def build_engine(config: DictateConfig) -> ASREngine:
    """Return the ASR engine selected by ``config.engine``."""
    if config.engine == "whisper":
        from .whisper import WhisperEngine

        return WhisperEngine(
            model_name=config.whisper_model,
            device=config.whisper_device,
            compute_type="int8_float16",
            language=config.language,
            num_threads=config.num_threads,
        )
    return ParakeetEngine(
        num_threads=config.num_threads,
        provider=config.provider,
    )
