"""The compute type has to come from the card, not from a constant.

A GTX 1080 stopped the setup with "Requested int8_float16 compute type, but the target
device or backend do not support efficient int8_float16 computation", after the whole
1.6 GB model had already downloaded. Pascal has fp16 at a fraction of fp32 throughput, so
CTranslate2 refuses that combination outright.
"""

from __future__ import annotations

import pytest

from dictate.asr.whisper import WhisperEngine

PASCAL = {"float32", "int8", "int8_float32"}          # a GTX 1080
AMPERE = {"float32", "float16", "bfloat16", "int8", "int8_float32", "int8_float16",
          "int8_bfloat16"}                            # an RTX 3090, measured


def _engine(monkeypatch, supported):
    class FakeCT2:
        @staticmethod
        def get_supported_compute_types(device):
            return supported

    monkeypatch.setitem(__import__("sys").modules, "ctranslate2", FakeCT2)
    return WhisperEngine(device="cuda", compute_type="auto")


def test_a_pascal_card_gets_int8_float32(monkeypatch):
    assert _engine(monkeypatch, PASCAL)._resolve_compute_type() == "int8_float32"


def test_a_modern_card_still_gets_the_fast_one(monkeypatch):
    """The control. If both cards resolved the same way the choice would be doing nothing."""
    assert _engine(monkeypatch, AMPERE)._resolve_compute_type() == "int8_float16"


def test_an_explicit_choice_in_the_config_is_obeyed(monkeypatch):
    engine = _engine(monkeypatch, PASCAL)
    engine.compute_type = "float32"
    assert engine._resolve_compute_type() == "float32"


def test_an_unreadable_backend_falls_back_to_plain_int8(monkeypatch):
    class Broken:
        @staticmethod
        def get_supported_compute_types(device):
            raise RuntimeError("no CUDA here")

    monkeypatch.setitem(__import__("sys").modules, "ctranslate2", Broken)
    assert WhisperEngine(device="cuda", compute_type="auto")._resolve_compute_type() == "int8"


@pytest.mark.parametrize("supported", [PASCAL, AMPERE])
def test_the_choice_is_always_one_the_device_supports(monkeypatch, supported):
    assert _engine(monkeypatch, supported)._resolve_compute_type() in supported
