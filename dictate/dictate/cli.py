"""CLI helpers for test-mic, transcribe, and download-model.

Phase 1 implements only the parts that do not need the ASR engine yet.
The remaining commands raise a clear error until their phase lands.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .config import DictateConfig, load_config


def _load(config_path: Path | None) -> DictateConfig:
    return load_config(config_path)


def test_mic(seconds: int, config_path: Path | None = None) -> int:
    """Record ``seconds`` from the microphone and transcribe to console.

    Implemented in phase 2 (recorder) and phase 3 (ASR).
    """
    _load(config_path)
    print("--test-mic is not implemented yet (phase 2).", file=sys.stderr)
    return 1


def transcribe_file(path: Path, config_path: Path | None = None) -> int:
    """Transcribe a wav file and print timing and text.

    Implemented in phase 3 (ASR).
    """
    _load(config_path)
    print("--transcribe is not implemented yet (phase 3).", file=sys.stderr)
    return 1


def download_model(config_path: Path | None = None) -> int:
    """Download the default ASR model.

    Implemented in phase 3 (model manager).
    """
    _load(config_path)
    print("--download-model is not implemented yet (phase 3).", file=sys.stderr)
    return 1
