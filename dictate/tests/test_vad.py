"""Tests for VAD trimming and resampling."""

from __future__ import annotations

import pathlib
import wave

import numpy as np
import pytest

from dictate.asr import models
from dictate.audio.resample import resample
from dictate.audio.vad import VAD_SAMPLE_RATE, SileroVAD

requires_vad = pytest.mark.skipif(
    not models.is_vad_installed(),
    reason="silero_vad.onnx not downloaded",
)


SAMPLE = pathlib.Path(__file__).parent.parent / "assets" / "selftest.wav"


def _require_sample() -> None:
    """Skip rather than fail when no speech sample is on disk.

    These tests need real speech, and no speech clip is committed: the only recordings on
    hand are the owner's voice and this repository is public. They used to read
    `test_wavs/en.wav` out of the parakeet archive, which no longer exists now that the
    Parakeet engine is gone, so the skip reason named a file nobody could produce.

    To run them, put any 16 kHz mono wav of speech at ``assets/selftest.wav``.
    """
    if not SAMPLE.is_file():
        pytest.skip("no speech sample at %s" % SAMPLE)


def _load_model_test_wav() -> tuple[np.ndarray, int]:
    _require_sample()
    """Load a real speech sample shipped with the ASR model bundle."""
    wave_path = SAMPLE
    with wave.open(str(wave_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        raw = wav_file.readframes(wav_file.getnframes())
    pcm = np.frombuffer(raw, dtype=np.int16)
    if channels > 1:
        pcm = pcm.reshape(-1, channels)[:, 0]
    return pcm.astype(np.float32) / 32767.0, sample_rate


def test_resample_changes_length() -> None:
    samples = np.ones(16000, dtype=np.float32)
    out = resample(samples, 16000, 8000)
    assert out.size == 8000
    assert out[0] == 1.0
    assert out[-1] == 1.0


def test_resample_same_rate_is_noop() -> None:
    samples = np.ones(10, dtype=np.float32)
    out = resample(samples, 16000, 16000)
    assert out.size == 10


def test_resample_empty() -> None:
    out = resample(np.zeros(0, dtype=np.float32), 44100, 16000)
    assert out.size == 0


@requires_vad
def test_trim_removes_leading_and_trailing_silence() -> None:
    speech, sample_rate = _load_model_test_wav()
    silence = np.zeros(2 * sample_rate, dtype=np.float32)
    padded = np.concatenate([silence, speech, silence])

    vad = SileroVAD()
    trimmed = vad.trim(padded, sample_rate, preroll_ms=100, tail_pad_ms=100)

    # At least 1.5 s of leading silence must be removed (preroll is only
    # 100 ms; Silero may lag the true onset by a window or two).
    removed = padded.size / sample_rate * VAD_SAMPLE_RATE - trimmed.size
    assert removed >= 2 * VAD_SAMPLE_RATE
    # Speech content must survive: at least half the speech duration.
    speech_16k = speech.size / sample_rate * VAD_SAMPLE_RATE
    assert trimmed.size >= speech_16k * 0.5


@requires_vad
def test_trim_rejects_silence_only() -> None:
    vad = SileroVAD()
    silence = np.zeros(2 * VAD_SAMPLE_RATE, dtype=np.float32)
    assert vad.trim(silence, VAD_SAMPLE_RATE).size == 0


@requires_vad
def test_has_speech() -> None:
    speech, sample_rate = _load_model_test_wav()
    vad = SileroVAD()
    assert vad.has_speech(speech, sample_rate) is True
    assert vad.has_speech(np.zeros(sample_rate, dtype=np.float32), sample_rate) is False


def test_recorder_drain_concatenates_queue() -> None:
    from dictate.audio.recorder import Recorder

    recorder = Recorder()
    recorder._queue.put(np.array([0.1, 0.2], dtype=np.float32))
    recorder._queue.put(np.array([0.3], dtype=np.float32))
    audio = recorder.drain()
    assert np.allclose(audio, [0.1, 0.2, 0.3])
    assert recorder.drain().size == 0
