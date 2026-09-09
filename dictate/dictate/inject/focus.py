"""Foreground window tracking: capture the target and restore focus."""

from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)

try:
    import win32gui
    import win32process

    _WIN32_OK = True
except ImportError:  # pragma: no cover - Windows dependency
    _WIN32_OK = False

# Window classes that are never valid paste targets.
_NON_TARGET_CLASSES = ("#32768", "Shell_TrayWnd", "Shell_SecondaryTrayWnd")

VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002


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
    """Bring ``hwnd`` to the foreground and verify it actually moved.

    Windows blocks SetForegroundWindow from background processes; a
    brief synthetic ALT press unlocks it. The result is verified against
    the real foreground window after the call.
    """
    if not _WIN32_OK or not hwnd:
        return False
    import ctypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    try:
        # Already in the foreground: nothing to do, and an ALT tap here
        # would open the target window menu bar instead.
        if win32gui.GetForegroundWindow() == hwnd:
            return True
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.05)
        if win32gui.GetForegroundWindow() == hwnd:
            return True
        # Blocked: the synthetic ALT press unlocks SetForegroundWindow.
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.05)
        actual = win32gui.GetForegroundWindow()
        ok = actual == hwnd
        if not ok:
            logger.warning(
                "restore_focus: wanted hwnd=%s, foreground stayed hwnd=%s", hwnd, actual
            )
        return ok
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
