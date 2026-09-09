"""Model download and verification.

Downloads the int8 Parakeet TDT v3 bundle into
``%LOCALAPPDATA%/Dictate/models/`` and verifies the extracted files.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..config import app_data_dir

logger = logging.getLogger(__name__)

MODELS_DIR_NAME = "models"
MODEL_NAME = "parakeet-tdt-0.6b-v3-int8"
ARCHIVE_DIR_NAME = "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"
MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2"
)
ARCHIVE_NAME = "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2"

REQUIRED_FILES = (
    "encoder.int8.onnx",
    "decoder.int8.onnx",
    "joiner.int8.onnx",
    "tokens.txt",
)


@dataclass
class ModelPaths:
    """Paths to the model files."""

    encoder: Path
    decoder: Path
    joiner: Path
    tokens: Path
    directory: Path


def models_dir() -> Path:
    """Return the models directory."""
    return app_data_dir() / MODELS_DIR_NAME


def model_dir() -> Path:
    """Return the directory for the default model.

    The tar archive extracts to ``sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8``.
    We keep the extracted name and expose it as the model directory.
    """
    return models_dir() / ARCHIVE_DIR_NAME


def _sha256(path: Path) -> str:
    """Return the SHA256 of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_model_installed() -> bool:
    """Return True if the model directory exists and has all required files."""
    directory = model_dir()
    if not directory.is_dir():
        return False
    for name in REQUIRED_FILES:
        path = directory / name
        if not path.is_file() or path.stat().st_size == 0:
            return False
    return True


def model_paths() -> ModelPaths:
    """Return the paths to the model files.

    Raises FileNotFoundError if the model is not installed.
    """
    directory = model_dir()
    if not is_model_installed():
        raise FileNotFoundError(
            f"Model not installed. Run `python -m dictate --download-model` "
            f"to download it into {directory}"
        )
    return ModelPaths(
        encoder=directory / "encoder.int8.onnx",
        decoder=directory / "decoder.int8.onnx",
        joiner=directory / "joiner.int8.onnx",
        tokens=directory / "tokens.txt",
        directory=directory,
    )


def download_model(progress_callback=None) -> Path:
    """Download and extract the default model.

    Returns the model directory. Skips the download if the model is
    already installed.
    """
    directory = model_dir()
    if is_model_installed():
        logger.info("Model already installed at %s", directory)
        return directory

    models_dir().mkdir(parents=True, exist_ok=True)
    archive_path = models_dir() / ARCHIVE_NAME

    logger.info("Downloading %s", MODEL_URL)
    urllib.request.urlretrieve(MODEL_URL, archive_path, reporthook=progress_callback)

    logger.info("Extracting %s", archive_path)
    with tarfile.open(archive_path, "r:bz2") as tar:
        tar.extractall(models_dir(), filter="data")

    archive_path.unlink(missing_ok=True)

    if not is_model_installed():
        raise RuntimeError(
            f"Model extraction failed: expected files missing in {directory}"
        )

    logger.info("Model installed at %s", directory)
    return directory


def remove_model() -> None:
    """Remove the downloaded model directory."""
    directory = model_dir()
    if directory.is_dir():
        shutil.rmtree(directory)
        logger.info("Removed model at %s", directory)
