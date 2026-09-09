"""SendInput keyboard injection: unicode typing and modifier combos."""

from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes

from .base import TextInjector

logger = logging.getLogger(__name__)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_CONTROL = 0x11


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT)]


_COMBOS: dict[str, int] = {
    "ctrl": VK_CONTROL,
    "control": VK_CONTROL,
    "alt": VK_MENU,
    "shift": VK_SHIFT,
}


def _user32():
    return ctypes.WinDLL("user32", use_last_error=True)


def _vk_for(name: str) -> int:
    """Return the virtual key code for a combo element."""
    name = name.strip().lower()
    if name in _COMBOS:
        return _COMBOS[name]
    if len(name) == 1:
        return ord(name.upper())
    raise ValueError(f"Unsupported paste-combo element: {name!r}")


def _unicode_input(code: int, keyup: bool) -> INPUT:
    item = INPUT()
    item.type = INPUT_KEYBOARD
    item.ki = KEYBDINPUT(
        wVk=0,
        wScan=code,
        dwFlags=KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if keyup else 0),
        time=0,
        dwExtraInfo=None,
    )
    return item


def _key_event(vk: int, keyup: bool) -> INPUT:
    item = INPUT()
    item.type = INPUT_KEYBOARD
    item.ki = KEYBDINPUT(
        wVk=vk,
        wScan=0,
        dwFlags=KEYEVENTF_KEYUP if keyup else 0,
        time=0,
        dwExtraInfo=None,
    )
    return item


def send_unicode(text: str, delay_ms: int = 0) -> None:
    """Type ``text`` character by character via KEYEVENTF_UNICODE."""
    user32 = _user32()
    for char in text:
        code = ord(char)
        parts = [code]
        if code > 0xFFFF:
            parts = [
                0xD800 + ((code - 0x10000) >> 10),
                0xDC00 + ((code - 0x10000) & 0x3FF),
            ]
        for part in parts:
            for keyup in (False, True):
                event = _unicode_input(part, keyup=keyup)
                user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
                if delay_ms:
                    time.sleep(delay_ms / 1000)


def send_combo(combo: str, delay_ms: int = 0) -> None:
    """Press and release a modifier combo such as ``ctrl+v``."""
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if not parts:
        raise ValueError("Empty paste combo")
    keys = [_vk_for(part) for part in parts]
    mods, tap = keys[:-1], keys[-1]
    user32 = _user32()

    for vk in mods:
        user32.SendInput(1, ctypes.byref(_key_event(vk, keyup=False)), ctypes.sizeof(INPUT))
    time.sleep(0.02)
    user32.SendInput(1, ctypes.byref(_key_event(tap, keyup=False)), ctypes.sizeof(INPUT))
    if delay_ms:
        time.sleep(delay_ms / 1000)
    user32.SendInput(1, ctypes.byref(_key_event(tap, keyup=True)), ctypes.sizeof(INPUT))
    for vk in reversed(mods):
        user32.SendInput(1, ctypes.byref(_key_event(vk, keyup=True)), ctypes.sizeof(INPUT))


class SendInputInjector(TextInjector):
    """Type text character by character with KEYEVENTF_UNICODE."""

    def __init__(self, delay_ms: int = 0, prefix_space: str = "auto") -> None:
        self.delay_ms = delay_ms
        self.prefix_space = prefix_space

    def insert(self, text: str, target_hwnd: int = 0) -> None:
        """Type ``text`` into ``target_hwnd`` (0 = current foreground)."""
        if not text:
            return
        if target_hwnd:
            from . import focus

            ok = focus.restore_focus(target_hwnd)
            logger.info("SendInput: refocus hwnd=%s ok=%s", target_hwnd, ok)
        payload = self._prefixed(text)
        time.sleep(0.05)  # let focus settle
        send_unicode(payload, self.delay_ms)

    def _prefixed(self, text: str) -> str:
        """Apply the prefix-space policy."""
        if self.prefix_space == "always":
            return " " + text
        if self.prefix_space == "never":
            return text
        first = text[:1]
        if first and not first.isspace() and first not in "([\"'":
            return " " + text
        return text
