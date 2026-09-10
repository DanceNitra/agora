"""Model download and verification.

Downloads the faster-whisper large-v3-turbo weights and the Silero VAD model into
``%LOCALAPPDATA%/Dictate/models/`` and verifies what landed on disk.

Whisper on the GPU is the only engine. The Parakeet engine that used to sit beside it
auto-detected Slovak as Polish and returned Polish orthography, so it was removed rather
than kept as a CPU fallback: an engine that returns the wrong language is worse than a
refusal, because the user has to read the output to find out.
"""

from __future__ import annotations

import logging
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..config import app_data_dir

logger = logging.getLogger(__name__)

MODELS_DIR_NAME = "models"

# CTranslate2 weights for Whisper large-v3-turbo. faster-whisper resolves the alias
# "large-v3-turbo" to this repository, and the installer downloads it explicitly so the
# app never depends on a warm Hugging Face cache on the machine it is installed on.
WHISPER_DIR_NAME = "faster-whisper-large-v3-turbo"
WHISPER_REPO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"

# Measured on the installed snapshot on 2026-09-10: model.bin is 1,617,884,929 bytes and
# the five files total 1,621,667,008. The floors are an order of magnitude below the real
# sizes, so a truncated or stubbed file fails and a future re-quantization still passes.
WHISPER_FILES = {
    "model.bin": 1_000_000_000,
    "config.json": 500,
    "preprocessor_config.json": 100,
    "tokenizer.json": 1_000_000,
    "vocabulary.json": 100_000,
}

VAD_MODEL_FILE = "silero_vad.onnx"
VAD_MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "silero_vad.onnx"
)
VAD_MIN_BYTES = 500_000


@dataclass
class ModelPaths:
    """Paths to the installed model files."""

    weights: Path
    tokenizer: Path
    directory: Path


def models_dir() -> Path:
    """Return the models directory."""
    return app_data_dir() / MODELS_DIR_NAME


def model_dir() -> Path:
    """Return the directory holding the Whisper weights."""
    return models_dir() / WHISPER_DIR_NAME


def is_model_installed() -> bool:
    """Return True if every Whisper file exists at a plausible size.

    A weight file that is a few bytes is not a weight file. The check used to ask only
    that the size was non-zero, and four one-byte stubs left behind by a test passed it:
    ``--download-model`` skipped the download and printed "Model installed at ...".
    An installer that reports success over a stub is worse than one that fails.
    """
    directory = model_dir()
    if not directory.is_dir():
        return False
    for name, floor in WHISPER_FILES.items():
        path = directory / name
        if not path.is_file() or path.stat().st_size < floor:
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
        weights=directory / "model.bin",
        tokenizer=directory / "tokenizer.json",
        directory=directory,
    )


def is_vad_installed() -> bool:
    """Return True if the Silero VAD model exists at a plausible size."""
    path = models_dir() / VAD_MODEL_FILE
    return path.is_file() and path.stat().st_size >= VAD_MIN_BYTES


def vad_model_path() -> Path:
    """Return the path to the Silero VAD model.

    Raises FileNotFoundError if the model is not installed.
    """
    path = models_dir() / VAD_MODEL_FILE
    if not is_vad_installed():
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


def _download_whisper(progress_callback=None) -> Path:
    """Download the Whisper snapshot into the app's own models directory."""
    from huggingface_hub import snapshot_download

    directory = model_dir()
    directory.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        WHISPER_REPO,
        local_dir=str(directory),
        allow_patterns=list(WHISPER_FILES),
    )
    if progress_callback is not None:
        progress_callback(1, 1, 1)
    return directory


def download_model(progress_callback=None) -> Path:
    """Download the Whisper weights and the VAD model. Skips what is already installed.

    Returns the Whisper model directory.
    """
    directory = model_dir()
    if not is_model_installed():
        _download_whisper(progress_callback)
        if not is_model_installed():
            missing = [
                name
                for name, floor in WHISPER_FILES.items()
                if not (directory / name).is_file()
                or (directory / name).stat().st_size < floor
            ]
            raise RuntimeError(
                f"Whisper download failed: missing or truncated in {directory}: {missing}"
            )
        logger.info("Whisper installed at %s", directory)
    else:
        logger.info("Whisper already installed at %s", directory)

    if not is_vad_installed():
        models_dir().mkdir(parents=True, exist_ok=True)
        _download(VAD_MODEL_URL, models_dir() / VAD_MODEL_FILE, progress_callback)
        if not is_vad_installed():
            raise RuntimeError(f"VAD download failed: {models_dir() / VAD_MODEL_FILE}")
        logger.info("VAD model installed at %s", models_dir() / VAD_MODEL_FILE)
    return directory


def remove_model() -> None:
    """Remove the downloaded Whisper model directory."""
    directory = model_dir()
    if directory.is_dir():
        shutil.rmtree(directory)
        logger.info("Removed model at %s", directory)
