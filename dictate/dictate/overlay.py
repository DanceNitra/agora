"""pywebview control window: floating pill with a live waveform.

Replaces the tkinter HUD. The HTML page in ``dictate/ui/index.html``
polls a small JS API for state, waveform envelope points, and the last
transcript; the record button, config, and exit call back into Python.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import webview

from .app import DictationApp
from .inject import focus

logger = logging.getLogger(__name__)

UI_FILE = Path(__file__).parent / "ui" / "index.html"

STATUS_LABELS = {
    "IDLE": "PRIPRAVENÝ",
    "RECORDING": "NAHRÁVAM",
    "TRANSCRIBING": "PREPISUJEM…",
    "INJECTING": "VKLÁDAM…",
}


class WebViewWindow:
    """pywebview wrapper wired to the DictationApp state machine."""

    def __init__(self, app: DictationApp, stop_event) -> None:
        self.app = app
        self.stop_event = stop_event
        self.last_external = 0
        self._window = None
        self._pending_wave: list[float] = []
        self._transcript = ""
        app.add_state_listener(self.set_state)
        app.add_wave_listener(self.set_wave)
        app.add_transcript_listener(self.set_transcript)

    # -- state listener API ---------------------------------------------------

    def set_state(self, state: str) -> None:
        """State transitions are picked up by the JS status poll."""
        logger.debug("State -> %s", state)

    def set_wave(self, envelope: list[float]) -> None:
        """Buffer envelope points for the JS poller."""
        self._pending_wave.extend(envelope)

    def set_transcript(self, text: str) -> None:
        """Store the last transcript for the JS poller."""
        self._transcript = text

    # -- JS API ----------------------------------------------------------------

    def get_wave(self) -> list[float]:
        """Return buffered envelope points and clear them."""
        points = self._pending_wave
        self._pending_wave = []
        return points

    def get_status(self) -> dict:
        """Return the current state and last transcript for the UI."""
        with self.app._lock:
            state = self.app.state
        label = STATUS_LABELS.get(state, state)
        return {"state": state, "status": label, "transcript": self._transcript}

    def toggle_record(self) -> None:
        """Start or stop recording (record button)."""
        self.app.toggle_recording()

    def open_config(self) -> None:
        """Open the JSON config in the default editor."""
        import os

        from .config import default_config_path, save_config

        path = default_config_path()
        save_config(self.app.config, path)
        os.startfile(str(path))  # noqa: S606

    def exit(self) -> None:
        """Exit the app."""
        self.stop_event.set()

    # -- lifecycle ---------------------------------------------------------------

    def run(self) -> None:
        """Open the pill window and block until the user exits."""
        threading.Thread(target=self._track_foreground, daemon=True).start()
        self._window = webview.create_window(
            "Dictate",
            str(UI_FILE),
            js_api=self,
            width=404,
            height=158,
            frameless=True,
            on_top=True,
            easy_drag=False,
            background_color="#12141c",
            transparent=False,
            resizable=False,
        )
        webview.start()
        logger.info("WebView window closed")

    def quit(self) -> None:
        """Close the window (thread-safe)."""
        if self._window is not None:
            try:
                self._window.destroy()
            except Exception:
                logger.debug("Window destroy failed", exc_info=True)

    def _track_foreground(self) -> None:
        """Track the last external foreground window for the paste target."""

        while not self.stop_event.wait(0.1):
            hwnd = focus.get_foreground_window()
            if focus.is_external_window(hwnd):
                self.last_external = hwnd
        self.quit()

