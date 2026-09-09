"""Tests for the model manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from dictate.asr import models


def test_models_dir_uses_appdata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert models.models_dir() == tmp_path / "Dictate" / "models"


def test_model_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert models.model_dir() == tmp_path / "Dictate" / "models" / models.ARCHIVE_DIR_NAME


def test_is_model_installed_false_when_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert models.is_model_installed() is False


def test_is_model_installed_true_with_files(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    directory = models.model_dir()
    directory.mkdir(parents=True)
    for name in models.REQUIRED_FILES:
        (directory / name).write_bytes(b"x")
    assert models.is_model_installed() is True


def test_model_paths_raises_when_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="not installed"):
        models.model_paths()
