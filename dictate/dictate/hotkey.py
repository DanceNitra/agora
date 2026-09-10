"""Global hotkey via the ``keyboard`` library.

Uses Windows low-level hooks (WH_KEYBOARD_LL), which fire regardless of
focus, integrity level, or launch context. Supports hold and toggle.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Global hold/toggle hotkey driven by the ``keyboard`` library."""

    def __init__(
        self,
        combo: str,
        on_activate: Callable[[], None],
        on_deactivate: Callable[[], None],
        mode: str = "hold",
        poll_s: float = 0.03,
    ) -> None:
        self.combo_str = combo
        self.mode = mode
        self.on_activate = on_activate
        self.on_deactivate = on_deactivate
        self.poll_s = poll_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._active = False
        self._hook_installed = False

    def _wait_release(self) -> None:
        """Block until the combo is released, then call on_deactivate."""
        import keyboard

        while not self._stop.is_set() and keyboard.is_pressed(self.combo_str):
            self._stop.wait(self.poll_s)
        self._active = False
        logger.info("Hotkey released")
        try:
            self.on_deactivate()
        except Exception:
            logger.exception("Hotkey deactivate callback failed")

    def _on_press(self) -> None:
        """Callback when hotkey is pressed."""
        if self._active:
            return
        self._active = True
        logger.info("Hotkey activated (%s)", self.combo_str)
        try:
            self.on_activate()
        except Exception:
            logger.exception("Hotkey activate callback failed")
        if self.mode == "hold":
            threading.Thread(target=self._wait_release, daemon=True).start()

    def _loop(self) -> None:
        """Thread body: register hook and pump keyboard events."""
        import keyboard

        # 'on_press_key' fires on every press; we use is_pressed to filter.
        keyboard.add_hotkey(
            self.combo_str,
            lambda: self._on_press(),
            trigger_on_release=False,
        )
        self._hook_installed = True
        logger.info("Keyboard hook installed (%s, mode=%s)", self.combo_str, self.mode)
        while not self._stop.is_set():
            self._stop.wait(0.1)
        # Cleanup: remove hooks
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self._hook_installed = False
        logger.info("Keyboard hook removed")

    def start(self) -> None:
        """Start the hotkey listener thread."""
        if self._thread is None:
            self._stop = threading.Event()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the hotkey listener thread."""
        if self._thread is not None:
            self._stop.set()
            self._thread.join(timeout=2.0)
            self._thread = None
            self._active = False
            self._hook_installed = False

    def __str__(self) -> str:
        return self.combo_str
