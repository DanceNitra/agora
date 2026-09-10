"""Build the ASR engine.

There is one engine. Whisper large-v3-turbo on the GPU forces Slovak explicitly; the
Parakeet engine that used to be selectable here detected Slovak as Polish and wrote
Polish orthography, so it is gone rather than demoted to a fallback.
"""

from __future__ import annotations

from ..config import DictateConfig
from .base import ASREngine


def build_engine(config: DictateConfig) -> ASREngine:
    """Return the Whisper engine configured for this install."""
    from .whisper import WhisperEngine

    return WhisperEngine(
        model_name=config.whisper_model,
        device=config.whisper_device,
        compute_type="int8_float16",
        language=config.language,
        num_threads=config.num_threads,
    )
