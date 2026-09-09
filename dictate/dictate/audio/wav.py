"""WAV file writing for recorded audio."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def write_wav(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    """Write ``samples`` (float32 in [-1, 1]) to a 16-bit mono WAV file."""
    if samples.ndim != 1:
        raise ValueError(f"Expected 1-D samples, got shape {samples.shape}")
    pcm = np.clip(samples, -1.0, 1.0)
    pcm16 = (pcm * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm16.tobytes())
