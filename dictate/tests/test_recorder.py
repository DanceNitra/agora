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


# -- device identity across a reboot -------------------------------------------
#
# Measured on the live log 2026-09-10: index 5 was "Microphone (HyperX Quadcast)"
# until 13:09 and "Line 1/2 (M-Audio AIR 192 4)" at 13:25, either side of one
# reboot. The saved config was intact and still said 5, so Dictate recorded
# silence from the wrong input and reported no error. These fixtures are that
# renumbering.

_BEFORE_REBOOT = [
    {"name": "Microsoft Sound Mapper - Input", "max_input_channels": 2},
    {"name": "Microphone (Voicemod Virtual Au", "max_input_channels": 2},
    {"name": "Microphone (Camo)", "max_input_channels": 2},
    {"name": "Headset Microphone (Oculus Virt", "max_input_channels": 1},
    {"name": "Microphone (Sonic Studio Virtua", "max_input_channels": 2},
    {"name": "Microphone (HyperX Quadcast)", "max_input_channels": 2},
]
_AFTER_REBOOT = [
    {"name": "Microsoft Sound Mapper - Input", "max_input_channels": 2},
    {"name": "Microphone (Voicemod Virtual Au", "max_input_channels": 2},
    {"name": "Microphone (Camo)", "max_input_channels": 2},
    {"name": "Headset Microphone (Oculus Virt", "max_input_channels": 1},
    {"name": "Microphone (Sonic Studio Virtua", "max_input_channels": 2},
    {"name": "Line 1/2 (M-Audio AIR 192 4)", "max_input_channels": 2},
    {"name": "Microphone (HyperX Quadcast)", "max_input_channels": 2},
]


def _patch_devices(monkeypatch: pytest.MonkeyPatch, devices: list[dict]) -> None:
    import dictate.audio.recorder as recorder_module

    monkeypatch.setattr(recorder_module.sd, "query_devices", lambda: devices)


def test_the_fixtures_really_renumber() -> None:
    """Control: if the fixtures stop reproducing the shift, the tests below are void."""
    assert _BEFORE_REBOOT[5]["name"] == "Microphone (HyperX Quadcast)"
    assert _AFTER_REBOOT[5]["name"] == "Line 1/2 (M-Audio AIR 192 4)"
    assert _BEFORE_REBOOT[5]["name"] != _AFTER_REBOOT[5]["name"]


def test_a_saved_name_survives_renumbering(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_devices(monkeypatch, _BEFORE_REBOOT)
    assert resolve_device("Microphone (HyperX Quadcast)") == 5

    _patch_devices(monkeypatch, _AFTER_REBOOT)
    assert resolve_device("Microphone (HyperX Quadcast)") == 6


def test_a_saved_index_does_not_survive_renumbering(monkeypatch: pytest.MonkeyPatch) -> None:
    """The defect itself: an index resolves, and points at the wrong microphone."""
    _patch_devices(monkeypatch, _AFTER_REBOOT)
    assert resolve_device(5) == 5
    assert _AFTER_REBOOT[5]["name"] != "Microphone (HyperX Quadcast)"


def test_resolve_device_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_devices(monkeypatch, _AFTER_REBOOT)
    assert resolve_device("hyperx quadcast") == 6


def test_resolve_device_skips_output_only(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_devices(monkeypatch, [
        {"name": "Speakers (HyperX Quadcast)", "max_input_channels": 0},
        {"name": "Microphone (HyperX Quadcast)", "max_input_channels": 2},
    ])
    assert resolve_device("HyperX Quadcast") == 1


def test_missing_device_falls_back_and_warns(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _patch_devices(monkeypatch, _AFTER_REBOOT)
    with caplog.at_level("WARNING"):
        assert resolve_device("Blue Yeti") is None
    assert "Blue Yeti" in caplog.text
