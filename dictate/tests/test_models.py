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
    assert models.model_dir() == tmp_path / "Dictate" / "models" / models.WHISPER_DIR_NAME


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
    for name, floor in models.WHISPER_FILES.items():
        # Plausible sizes, not a byte: is_model_installed has a floor per file, and it
        # has one because one-byte fixtures from this very test escaped into the real
        # model directory and the installer called them a model.
        (directory / name).write_bytes(b"x" * (floor + 1))
    assert models.is_model_installed() is True


def test_a_truncated_weight_file_is_not_an_installed_model(monkeypatch, tmp_path) -> None:
    """The floor is the point of the check, so one file below it must fail.

    Without this the test above passes against a check that only asks whether the files
    exist, which is the exact defect the floors were added for.
    """
    monkeypatch.setattr(models, "app_data_dir", lambda: tmp_path / "Dictate")
    directory = models.model_dir()
    directory.mkdir(parents=True)
    for name, floor in models.WHISPER_FILES.items():
        size = 1 if name == "model.bin" else floor + 1
        (directory / name).write_bytes(b"x" * size)
    assert models.is_model_installed() is False


def test_model_paths_raises_when_missing(monkeypatch, tmp_path: Path) -> None:
    # Patch the name inside models, not in config: models does `from ..config import
    # app_data_dir`, so it holds its own reference and a patch on config never reaches it.
    monkeypatch.setattr(models, "app_data_dir", lambda: tmp_path / "Dictate")
    with pytest.raises(FileNotFoundError, match="not installed"):
        models.model_paths()
