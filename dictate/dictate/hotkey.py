"""Global hotkey via GetAsyncKeyState polling.

Polling the key state every ~30 ms needs no window hooks, so it works
in any process regardless of hook registration quirks. Supports hold
(hotkey down starts, trigger release stops) and toggle (press to start,
press again to stop) modes.
"""

from __future__ import annotations

import ctypes
import logging
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)

# Generic virtual keys: GetAsyncKeyState(VK_CONTROL) matches either the
# left or the right variant, so the generic code is the only one needed.
_VK_ALIASES: dict[str, set[int]] = {
    "ctrl": {0x11},
    "alt": {0x12},
    "shift": {0x10},
    "space": {0x20},
    "enter": {0x0D},
    "tab": {0x09},
}

_MODIFIER_NAMES = {"ctrl", "alt", "shift"}


def _vk_codes(name: str) -> set[int]:
    """Return the set of virtual key codes a combo element matches."""
    name = name.strip().lower()
    if name in _VK_ALIASES:
        return _VK_ALIASES[name]
    if len(name) == 1:
        return {ord(name.upper())}
    if name.startswith("f") and name[1:].isdigit():
        number = int(name[1:])
        if 1 <= number <= 24:
            return {0x70 + number - 1}
    raise ValueError(f"Unsupported hotkey element: {name!r}")


class HotkeyListener:
    """Global hold/toggle hotkey driven by a polling thread."""

    def __init__(
        self,
        combo: str,
        on_activate: Callable[[], None],
        on_deactivate: Callable[[], None],
        mode: str = "hold",
        poll_s: float = 0.03,
    ) -> None:
        parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
        if len(parts) < 2:
            raise ValueError(f"Hotkey {combo!r} needs a modifier and a trigger")
        self.mode = mode
        self.on_activate = on_activate
        self.on_deactivate = on_deactivate
        self.poll_s = poll_s
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._modifier_vks: set[int] = set()
        for part in parts[:-1]:
            self._modifier_vks |= _vk_codes(part)
        self._trigger_vks = _vk_codes(parts[-1])
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._active = False
        self._combo_edge = False

    def _vk_down(self, vk: int) -> bool:
        """Return True when the virtual key is physically down."""
        return bool(self._user32.GetAsyncKeyState(vk) & 0x8000)

    def _combo_down(self) -> bool:
        """Return True when all modifiers and the trigger are down."""
        return all(self._vk_down(vk) for vk in self._modifier_vks) and any(
            self._vk_down(vk) for vk in self._trigger_vks
        )

    def _loop(self) -> None:
        logger.info(
            "Hotkey poller started (mode=%s, %d modifier VKs, %d trigger VKs)",
            self.mode,
            len(self._modifier_vks),
            len(self._trigger_vks),
        )
        while not self._stop.is_set():
            combo = self._combo_down()
            if self.mode == "hold":
                if combo and not self._active:
                    self._active = True
                    logger.info("Hotkey activated (%s)", self)
                    try:
                        self.on_activate()
                    except Exception:
                        logger.exception("Hotkey activate callback failed")
                elif self._active and not combo:
                    self._active = False
                    logger.info("Hotkey released")
                    try:
                        self.on_deactivate()
                    except Exception:
                        logger.exception("Hotkey deactivate callback failed")
            else:  # toggle
                if combo and not self._combo_edge:
                    self._combo_edge = True
                    self._active = not self._active
                    callback = self.on_activate if self._active else self.on_deactivate
                    try:
                        callback()
                    except Exception:
                        logger.exception("Hotkey toggle callback failed")
                elif not combo:
                    self._combo_edge = False
            self._stop.wait(self.poll_s)

    def start(self) -> None:
        """Start the polling thread."""
        if self._thread is None:
            self._stop = threading.Event()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the polling thread."""
        if self._thread is not None:
            self._stop.set()
            self._thread.join(timeout=1.0)
            self._thread = None
            self._active = False

    def __str__(self) -> str:
        return f"{sorted(self._modifier_vks)}+{sorted(self._trigger_vks)}"

