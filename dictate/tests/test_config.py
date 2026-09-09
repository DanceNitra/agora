"""Tests for config load/save round-trip and validation."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from dictate.config import DictateConfig, load_config, save_config


def test_defaults() -> None:
    config = DictateConfig()
    assert config.hotkey == "ctrl+alt+space"
    assert config.hotkey_mode == "hold"
    assert config.engine == "parakeet"
    assert config.language == "sk"
    assert config.insert_mode == "clipboard"
    assert config.vad_enabled is True
    assert config.llm_cleanup.enabled is False


def test_round_trip(tmp_path) -> None:
    config = DictateConfig(
        hotkey="ctrl+shift+space",
        language="cs",
        microphone="Microphone (Realtek)",
        insert_mode="sendinput",
        app_overrides={"WindowsTerminal.exe": {"insert_mode": "sendinput"}},
    )
    path = tmp_path / "config.json"
    saved = save_config(config, path)
    assert saved == path
    assert path.exists()

    loaded = load_config(path)
    assert loaded == config


def test_load_missing_returns_defaults(tmp_path) -> None:
    path = tmp_path / "does-not-exist.json"
    config = load_config(path)
    assert config == DictateConfig()


def test_load_round_trip_preserves_diacritics(tmp_path) -> None:
    config = DictateConfig()
    path = tmp_path / "config.json"
    save_config(config, path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["language"] == "sk"
    loaded = load_config(path)
    assert loaded.language == "sk"


def test_invalid_language_rejected() -> None:
    with pytest.raises(ValidationError):
        DictateConfig(language="de")


def test_invalid_log_level_rejected() -> None:
    with pytest.raises(ValidationError):
        DictateConfig(log_level="VERBOSE")


def test_version_migration_sets_current(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"version": 1, "hotkey": "ctrl+space"}), encoding="utf-8")
    config = load_config(path)
    assert config.version == 1
    assert config.hotkey == "ctrl+space"


def test_newer_version_rejected(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"version": 99}), encoding="utf-8")
    with pytest.raises(ValueError, match="newer"):
        load_config(path)
