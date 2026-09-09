"""Clipboard-based text insertion: save, paste, restore after a delay."""

from __future__ import annotations

import logging
import threading

from .base import TextInjector
from .sendinput import send_combo

logger = logging.getLogger(__name__)

CF_UNICODETEXT = 13


class ClipboardInjector(TextInjector):
    """Save the clipboard, paste via a shortcut, then restore it.

    Only textual clipboard content is restored; if the original clipboard
    held binary data (for example an image) the dictated text is left in
    place and a warning is logged.
    """

    def __init__(
        self,
        paste_shortcut: str = "ctrl+v",
        restore_delay_ms: int = 300,
        refocus_original_window: bool = True,
        prefix_space: str = "auto",
    ) -> None:
        self.paste_shortcut = paste_shortcut
        self.restore_delay_ms = restore_delay_ms
        self.refocus_original_window = refocus_original_window
        self.prefix_space = prefix_space

    def insert(self, text: str, target_hwnd: int = 0) -> None:
        """Insert ``text`` into ``target_hwnd`` (0 = current foreground)."""
        import win32clipboard

        if not text:
            return
        payload = self._prefixed(text)

        original_text = self._clipboard_text()

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(CF_UNICODETEXT, payload)
        finally:
            win32clipboard.CloseClipboard()

        if self.refocus_original_window and target_hwnd:
            ok = focus_restore(target_hwnd)
            logger.info("Paste: refocus hwnd=%s ok=%s", target_hwnd, ok)
        else:
            logger.info("Paste: refocus disabled or no target; pasting into focused window")

        send_combo(self.paste_shortcut)
        logger.info("Paste: sent %s (%d chars)", self.paste_shortcut, len(payload))

        if self.restore_delay_ms:
            timer = threading.Timer(
                self.restore_delay_ms / 1000,
                self._restore_clipboard,
                args=(original_text,),
            )
            timer.daemon = True
            timer.start()
        else:
            self._restore_clipboard(original_text)

    @staticmethod
    def _clipboard_text() -> str | None:
        """Return the current clipboard text, or None when absent."""
        import win32clipboard

        try:
            win32clipboard.OpenClipboard()
        except Exception:
            logger.warning("Clipboard is locked; cannot save", exc_info=True)
            return None
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            return None
        except Exception:
            logger.warning("Could not read clipboard text", exc_info=True)
            return None
        finally:
            win32clipboard.CloseClipboard()

    @classmethod
    def _restore_clipboard(cls, original: str | None) -> None:
        """Restore the previous clipboard text if there was one."""
        if original is None:
            logger.info("Original clipboard held non-text data; not restoring")
            return
        import win32clipboard

        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(CF_UNICODETEXT, original)
            win32clipboard.CloseClipboard()
        except Exception:
            logger.warning("Could not restore clipboard text", exc_info=True)

    def _prefixed(self, text: str) -> str:
        """Apply the configured prefix-space policy."""
        if self.prefix_space == "always":
            return " " + text
        if self.prefix_space == "never":
            return text
        first = text[:1]
        if first and not first.isspace() and first not in "([\"'“„-–—":
            return " " + text
        return text


def focus_restore(hwnd: int) -> bool:
    """Import focus lazily so this module stays importable without pywin32."""
    from . import focus

    return focus.restore_focus(hwnd)
