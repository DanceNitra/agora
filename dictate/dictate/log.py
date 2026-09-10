"""Rotating log setup in ``%LOCALAPPDATA%/Dictate/logs``."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import app_data_dir

LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "dictate.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 5


def ensure_streams() -> None:
    """Give the process a stdout and a stderr, even when Windows gave it none.

    A windowed executable has no console, so ``sys.stdout`` and ``sys.stderr`` are None.
    Every ``print``, every ``logging.StreamHandler``, and every library that draws a
    progress bar then fails with "NoneType object has no attribute write".

    MEASURED: the packaged setup wizard died with exactly that on its download page,
    while the same code passed from a terminal, because a captured pipe is still a
    stream. Anything that only runs without a console needs this called first.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))


def setup_logging(level: str = "INFO", log_dir: Path | None = None) -> logging.Logger:
    """Configure the root logger and return it.

    Writes to a rotating file in the app data directory and to stderr.
    """
    ensure_streams()
    logger = logging.getLogger("dictate")
    logger.setLevel(level.upper())
    logger.propagate = False

    if logger.handlers:
        return logger

    log_path = (log_dir or app_data_dir() / LOG_DIR_NAME) / LOG_FILE_NAME
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
