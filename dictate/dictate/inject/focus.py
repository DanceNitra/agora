"""Foreground window tracking: capture the target and restore focus."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

try:
    import win32gui
    import win32process

    _WIN32_OK = True
except ImportError:  # pragma: no cover - Windows dependency
    _WIN32_OK = False

# Window classes that are never valid paste targets.
_NON_TARGET_CLASSES = ("#32768", "Shell_TrayWnd", "Shell_SecondaryTrayWnd")


def get_foreground_window() -> int:
    """Return the handle of the foreground window (0 when unavailable)."""
    if not _WIN32_OK:
        return 0
    return win32gui.GetForegroundWindow()


def is_external_window(hwnd: int) -> bool:
    """Return True when ``hwnd`` belongs to another app and can be a target.

    Excludes our own windows, the tray menu, and the taskbar.
    """
    if not _WIN32_OK or not hwnd:
        return False
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid == os.getpid():
            return False
        return win32gui.GetClassName(hwnd) not in _NON_TARGET_CLASSES
    except Exception:
        return False


def process_name(hwnd: int) -> str:
    """Return the lowercase executable name owning ``hwnd``."""
    if not _WIN32_OK or not hwnd:
        return ""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        import psutil

        return psutil.Process(pid).name().lower()
    except Exception:
        logger.debug("Could not resolve process name for hwnd=%s", hwnd, exc_info=True)
        return ""


def restore_focus(hwnd: int) -> bool:
    """Bring a previously captured window back to the foreground."""
    if not _WIN32_OK or not hwnd:
        return False
    try:
        win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        logger.warning("Could not restore focus to hwnd=%s", hwnd, exc_info=True)
        return False


def window_title(hwnd: int) -> str:
    """Return the window title for logging."""
    if not _WIN32_OK or not hwnd:
        return ""
    try:
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return ""
