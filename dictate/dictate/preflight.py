"""What this machine needs before Dictate can work, checked before anything downloads.

Each check returns ``(ok, detail)`` and says what is wrong in the words a user can act
on. They exist because the first install on a second machine failed halfway through the
setup, where the cause is buried in a log rather than on the screen.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# CTranslate2 is built against CUDA 12, and CUDA 12 needs a Windows driver from the 527
# series or newer. An older driver does not fail loudly: the model loads on the CPU.
MINIMUM_DRIVER = 527.41

# The window is a WebView2 control. Windows 11 and a current Windows 10 with Edge have the
# runtime; an older installation may not, and then the window never appears.
WEBVIEW2_CLIENT = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
WEBVIEW2_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"

REQUIRED_FREE_BYTES = 2_500_000_000


def _nvidia_smi(query: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"nvidia-smi did not run: {exc}"
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()[:200]
    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    return bool(line), line


def check_gpu() -> tuple[bool, str]:
    """Return whether an NVIDIA GPU with a working driver is present."""
    return _nvidia_smi("name,memory.total")


def check_driver() -> tuple[bool, str]:
    """Return whether the driver is new enough for CUDA 12.

    A failure here is worth reporting even though it is not fatal to the installer: the
    setup's own test transcription is the verdict, and it runs a page later.
    """
    ok, detail = _nvidia_smi("driver_version")
    if not ok:
        return False, detail
    try:
        version = float(".".join(detail.split(".")[:2]))
    except ValueError:
        return True, f"driver {detail}, version not parsed"
    if version < MINIMUM_DRIVER:
        return False, (f"driver {detail} is older than {MINIMUM_DRIVER}, which CUDA 12 "
                       f"needs. Update the NVIDIA driver.")
    return True, f"driver {detail}"


def check_webview2() -> tuple[bool, str]:
    """Return whether the WebView2 runtime is installed.

    Reads the version Edge's updater records for the runtime, in both registry views and
    for both the machine and the user, because a per-user install writes elsewhere.
    """
    import winreg

    roots = (
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\%s" % WEBVIEW2_CLIENT),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\EdgeUpdate\Clients\%s" % WEBVIEW2_CLIENT),
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\EdgeUpdate\Clients\%s" % WEBVIEW2_CLIENT),
    )
    for root, path in roots:
        try:
            with winreg.OpenKey(root, path) as key:
                version, _ = winreg.QueryValueEx(key, "pv")
                if version:
                    return True, f"WebView2 {version}"
        except OSError:
            continue
    return False, ("The WebView2 runtime is missing, so the window cannot open. "
                   "Install it from %s" % WEBVIEW2_URL)


def check_disk(target: Path | None = None) -> tuple[bool, str]:
    """Return whether the drive holding the models has room for them."""
    from .config import app_data_dir

    path = target or app_data_dir()
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    gigabytes = free / 1e9
    if free < REQUIRED_FREE_BYTES:
        return False, (f"{gigabytes:.1f} GB free on {probe.drive or probe}, and the "
                       f"model needs about 2 GB.")
    return True, f"{gigabytes:.1f} GB free"


def run_all() -> list[tuple[str, bool, str]]:
    """Run every check and return (label, ok, detail) in the order they matter."""
    return [
        ("Graphics card", *check_gpu()),
        ("Driver", *check_driver()),
        ("WebView2 runtime", *check_webview2()),
        ("Disk space", *check_disk()),
    ]
