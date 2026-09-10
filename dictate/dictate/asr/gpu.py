"""Is there an NVIDIA GPU, and did the model actually use it?

MEASURED 2026-09-10, and it removed a gigabyte of planned work. CTranslate2 4.8.2's
Windows wheel imports no CUDA library at all: its import table lists only the C runtime,
it links CUDA statically, and it ships ``cudnn64_9.dll`` beside itself. The packaged app,
with no ``nvidia`` package present and every CUDA directory stripped from PATH, still ran
Whisper on the GPU at RTF 0.116. So the installer downloads no CUDA runtime; the only
external requirement is ``nvcuda.dll``, which comes with the NVIDIA driver.

The arms that measured this are worth naming, because four of them were wrong before one
was right: transcript quality could not tell the arms apart once a sample-rate bug was
fixed, module enumeration failed twice and returned an empty list that read as evidence,
and the device attribute alone might only echo what was requested. What settled it was
asking the driver which processes hold GPU memory, with an empty arm as the control.
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def has_nvidia_gpu() -> tuple[bool, str]:
    """Return whether an NVIDIA GPU with a working driver is present, and what was found.

    Reads the driver through ``nvidia-smi``, which ships with the driver. The CUDA toolkit
    is irrelevant here: the app needs the driver, not the toolkit.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"nvidia-smi did not run: {exc}"
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()[:200]
    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    return bool(line), line
