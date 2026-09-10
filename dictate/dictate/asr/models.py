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


class Progress:
    """What a download has done so far, in bytes.

    The wizard needs bytes, not a spinner: a 1.6 GB file on a slow line takes long enough
    that a bar which only moves at the end is indistinguishable from a hung program. That
    is exactly what the first version showed on a second machine.
    """

    __slots__ = ("file", "file_done", "file_total", "done", "total", "bytes_per_second")

    def __init__(self, file, file_done, file_total, done, total, bytes_per_second):
        self.file = file
        self.file_done = file_done
        self.file_total = file_total
        self.done = done
        self.total = total
        self.bytes_per_second = bytes_per_second

    @property
    def fraction(self) -> float:
        return self.done / self.total if self.total else 0.0

    @property
    def seconds_left(self) -> float | None:
        if not self.bytes_per_second or not self.total:
            return None
        return max(self.total - self.done, 0) / self.bytes_per_second


def _content_length(url: str, timeout: float = 30.0) -> int:
    """Return the size of a URL, following redirects. Zero when the server will not say."""
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.headers.get("Content-Length") or 0)
    except Exception:
        logger.debug("HEAD failed for %s", url, exc_info=True)
        return 0


def _stream_to_file(url: str, destination: Path, on_chunk=None,
                    timeout: float = 60.0) -> Path:
    """Download ``url`` to ``destination``, resuming a partial file if one is there.

    ``on_chunk(file_done, file_total)`` is called as bytes arrive. The socket carries a
    timeout so a stalled connection raises instead of hanging the setup forever.
    """
    partial = destination.with_suffix(destination.suffix + ".part")
    have = partial.stat().st_size if partial.is_file() else 0
    total = _content_length(url, timeout=timeout)

    headers = {"Range": f"bytes={have}-"} if have else {}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if have and response.status != 206:
            # The server ignored the range, so start over rather than append to a prefix.
            have = 0
            partial.unlink(missing_ok=True)
        if not total:
            total = have + int(response.headers.get("Content-Length") or 0)
        mode = "ab" if have else "wb"
        with open(partial, mode) as sink:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                sink.write(chunk)
                have += len(chunk)
                if on_chunk is not None:
                    on_chunk(have, total)

    partial.replace(destination)
    return destination


def _whisper_file_url(name: str) -> str:
    """Return the direct URL of one file in the pinned Whisper repository."""
    return f"https://huggingface.co/{WHISPER_REPO}/resolve/main/{name}"


def _download_whisper(progress_callback=None) -> Path:
    """Download the Whisper files into the app's own models directory.

    Downloads them directly rather than through ``snapshot_download``, because that call
    reports progress only to a terminal, and this app has no terminal.
    """
    import time

    directory = model_dir()
    directory.mkdir(parents=True, exist_ok=True)

    wanted = [name for name, floor in WHISPER_FILES.items()
              if not (directory / name).is_file()
              or (directory / name).stat().st_size < floor]
    sizes = {name: _content_length(_whisper_file_url(name)) for name in wanted}
    total = sum(sizes.values()) or sum(WHISPER_FILES[name] for name in wanted)
    finished = 0
    started = time.monotonic()

    for name in wanted:
        logger.info("Downloading %s (%.1f MB)", name, sizes.get(name, 0) / 1e6)

        def on_chunk(file_done, file_total, name=name):
            if progress_callback is None:
                return
            elapsed = max(time.monotonic() - started, 1e-6)
            done = finished + file_done
            progress_callback(Progress(name, file_done, file_total, done, total,
                                       done / elapsed))

        _stream_to_file(_whisper_file_url(name), directory / name, on_chunk)
        finished += (directory / name).stat().st_size
        logger.info("Installed %s", name)

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
        _stream_to_file(VAD_MODEL_URL, models_dir() / VAD_MODEL_FILE)
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
