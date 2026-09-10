"""Tests for the model manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from dictate.asr import models


def test_models_dir_uses_appdata(monkeypatch, tmp_path: Path) -> None:
    # Patch the name inside models, not in config: models does `from ..config import
    # app_data_dir`, so it holds its own reference and a patch on config never reaches it.
    monkeypatch.setattr(models, "app_data_dir", lambda: tmp_path / "Dictate")
    assert models.models_dir() == tmp_path / "Dictate" / "models"


def test_model_dir(monkeypatch, tmp_path: Path) -> None:
    # Patch the name inside models, not in config: models does `from ..config import
    # app_data_dir`, so it holds its own reference and a patch on config never reaches it.
    monkeypatch.setattr(models, "app_data_dir", lambda: tmp_path / "Dictate")
    assert models.model_dir() == tmp_path / "Dictate" / "models" / models.ARCHIVE_DIR_NAME


def test_is_model_installed_false_when_missing(monkeypatch, tmp_path: Path) -> None:
    # Patch the name inside models, not in config: models does `from ..config import
    # app_data_dir`, so it holds its own reference and a patch on config never reaches it.
    monkeypatch.setattr(models, "app_data_dir", lambda: tmp_path / "Dictate")
    assert models.is_model_installed() is False


def test_is_model_installed_true_with_files(monkeypatch, tmp_path: Path) -> None:
    # Patch the name inside models, not in config: models does `from ..config import
    # app_data_dir`, so it holds its own reference and a patch on config never reaches it.
    monkeypatch.setattr(models, "app_data_dir", lambda: tmp_path / "Dictate")
    directory = models.model_dir()
    directory.mkdir(parents=True)
    for name in models.REQUIRED_FILES:
        # Plausible sizes, not a byte: is_model_installed now has a floor per file,
        # and it has one because one-byte fixtures from this very test escaped into
        # the real model directory and the installer called them a model.
        (directory / name).write_bytes(b"x" * (models.MIN_FILE_BYTES[name] + 1))
    assert models.is_model_installed() is True


def test_model_paths_raises_when_missing(monkeypatch, tmp_path: Path) -> None:
    # Patch the name inside models, not in config: models does `from ..config import
    # app_data_dir`, so it holds its own reference and a patch on config never reaches it.
    monkeypatch.setattr(models, "app_data_dir", lambda: tmp_path / "Dictate")
    with pytest.raises(FileNotFoundError, match="not installed"):
        models.model_paths()
