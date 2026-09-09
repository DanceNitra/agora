"""Tests for the audio recorder and wav writer."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

from dictate.audio.recorder import Recorder, resolve_device
from dictate.audio.wav import write_wav


def test_write_wav_round_trip(tmp_path: Path) -> None:
    samples = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float32)
    path = tmp_path / "test.wav"
    write_wav(path, samples, 16000)

    with wave.open(str(path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16000
        raw = wav_file.readframes(wav_file.getnframes())

    pcm = np.frombuffer(raw, dtype=np.int16)
    assert pcm[0] == 0
    assert pcm[1] == 16383  # int(0.5 * 32767)
    assert pcm[2] == -16383
    assert pcm[3] == 32767
    assert pcm[4] == -32767  # int(-1.0 * 32767)


def test_write_wav_rejects_2d(tmp_path: Path) -> None:
    samples = np.zeros((2, 2), dtype=np.float32)
    with pytest.raises(ValueError, match="1-D"):
        write_wav(tmp_path / "bad.wav", samples, 16000)


def test_recorder_drain_empty() -> None:
    recorder = Recorder()
    audio = recorder.drain()
    assert audio.size == 0
    assert audio.dtype == np.float32


def test_resolve_device_none() -> None:
    assert resolve_device(None) is None


def test_resolve_device_int() -> None:
    assert resolve_device(3) == 3
