"""Model download and verification.

Downloads the int8 Parakeet TDT v3 bundle and the Silero VAD model into
``%LOCALAPPDATA%/Dictate/models/`` and verifies the extracted files.
"""

from __future__ import annotations

import logging
import shutil
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..config import app_data_dir

logger = logging.getLogger(__name__)

MODELS_DIR_NAME = "models"
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

VAD_MODEL_FILE = "silero_vad.onnx"
VAD_MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "silero_vad.onnx"
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


# A weight file that is a few bytes is not a weight file. The check used to ask only that the
# size was non-zero, and four one-byte stubs left behind by a test passed it: `--download-model`
# skipped the download and printed "Model installed at ...". An installer that reports success
# over a stub is worse than one that fails.
MIN_FILE_BYTES = {
    "encoder.int8.onnx": 1_000_000,
    "decoder.int8.onnx": 100_000,
    "joiner.int8.onnx": 10_000,
    "tokens.txt": 1_000,
}


def is_model_installed() -> bool:
    """Return True if the model directory holds every required file at a plausible size."""
    directory = model_dir()
    if not directory.is_dir():
        return False
    for name in REQUIRED_FILES:
        path = directory / name
        if not path.is_file() or path.stat().st_size < MIN_FILE_BYTES.get(name, 1):
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


def is_vad_installed() -> bool:
    """Return True if the Silero VAD model file exists and is non-empty."""
    path = models_dir() / VAD_MODEL_FILE
    return path.is_file() and path.stat().st_size > 0


def vad_model_path() -> Path:
    """Return the path to the Silero VAD model.

    Raises FileNotFoundError if the model is not installed.
    """
    path = models_dir() / VAD_MODEL_FILE
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(
            f"VAD model not installed. Run `python -m dictate --download-model` "
            f"to download it into {path}"
        )
    return path


def _download(url: str, destination: Path, progress_callback=None) -> Path:
    """Download ``url`` into ``destination``."""
    logger.info("Downloading %s", url)
    urllib.request.urlretrieve(url, destination, reporthook=progress_callback)
    return destination


def download_model(progress_callback=None) -> Path:
    """Download and extract the default ASR model plus the VAD model.

    Returns the ASR model directory. Skips anything already installed.
    """
    directory = model_dir()
    if not is_model_installed():
        models_dir().mkdir(parents=True, exist_ok=True)
        archive_path = models_dir() / ARCHIVE_NAME

        _download(MODEL_URL, archive_path, progress_callback)
        logger.info("Extracting %s", archive_path)
        with tarfile.open(archive_path, "r:bz2") as tar:
            tar.extractall(models_dir(), filter="data")
        archive_path.unlink(missing_ok=True)

        if not is_model_installed():
            raise RuntimeError(
                f"Model extraction failed: expected files missing in {directory}"
            )
        logger.info("Model installed at %s", directory)
    else:
        logger.info("ASR model already installed at %s", directory)

    if not is_vad_installed():
        _download(VAD_MODEL_URL, models_dir() / VAD_MODEL_FILE, progress_callback)
        logger.info("VAD model installed at %s", models_dir() / VAD_MODEL_FILE)
    return directory


def remove_model() -> None:
    """Remove the downloaded model directory."""
    directory = model_dir()
    if directory.is_dir():
        shutil.rmtree(directory)
        logger.info("Removed model at %s", directory)
