"""CLI helpers for test-mic, transcribe, and download-model.

Phase 2 implements ``--test-mic`` with the recorder. The remaining
commands raise a clear error until their phase lands.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from .audio.recorder import Recorder, resolve_device
from .audio.wav import write_wav
from .config import DictateConfig, load_config


def _load(config_path: Path | None) -> DictateConfig:
    return load_config(config_path)


def test_mic(seconds: int, config_path: Path | None = None) -> int:
    """Record ``seconds`` from the microphone and save a wav file.

    Phase 2 does not transcribe yet; it verifies sample rate and range.
    """
    config = _load(config_path)
    device = resolve_device(config.microphone)
    recorder = Recorder(device=device)
    print(f"Recording {seconds} s from device {device or 'default'}...")
    audio = recorder.record(float(seconds))
    if audio.size == 0:
        print("No audio captured.", file=sys.stderr)
        return 1

    out_path = Path("test_mic.wav")
    write_wav(out_path, audio, recorder.sample_rate)
    duration = len(audio) / recorder.sample_rate
    peak = float(np.max(np.abs(audio)))
    print(f"Captured {duration:.2f} s, {len(audio)} samples, peak {peak:.4f}")
    print(f"Saved {out_path}")
    return 0


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
