"""System tray icon with states and a settings menu.

States render as coloured circles: green idle, red recording, orange
transcribing, amber injecting. The menu carries the record button,
"Open config" (plain JSON file), reload, and exit.
"""

from __future__ import annotations

import logging
import os
import threading

import pystray
from PIL import Image, ImageDraw

from .app import IDLE, RECORDING, DictationApp
from .config import default_config_path, save_config

logger = logging.getLogger(__name__)

STATE_COLORS = {
    "IDLE": (76, 175, 80),
    "RECORDING": (244, 67, 54),
    "TRANSCRIBING": (255, 152, 0),
    "INJECTING": (255, 193, 7),
}


def _state_image(state: str) -> Image.Image:
    """Render a filled circle for the state."""
    color = STATE_COLORS.get(state, STATE_COLORS["IDLE"])
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=color)
    if state == RECORDING:
        draw.ellipse((26, 26, 38, 38), fill=(255, 255, 255, 230))
    return image


class TrayUI:
    """pystray wrapper wired to the DictationApp state machine."""

    def __init__(self, app: DictationApp) -> None:
        self.app = app
        self.config_path = default_config_path()
        self.stop_event = threading.Event()
        self.icon = pystray.Icon(
            "dictate",
            _state_image(IDLE),
            "Dictate — idle",
            menu=pystray.Menu(
                pystray.MenuItem(
                    lambda _item: self._record_label(),
                    self._on_record,
                    default=True,
                ),
                pystray.MenuItem("Open config", self._on_open_config),
                pystray.MenuItem("Reload settings", self._on_reload),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._on_exit),
            ),
        )
        app.add_state_listener(self.set_state)

    def _record_label(self) -> str:
        if self.app.state == RECORDING:
            return "Stop recording"
        return "Record"

    def start(self) -> None:
        """Run the tray icon on its own thread (pystray run_detached)."""
        self.icon.run_detached()

    def set_state(self, state: str) -> None:
        """Reflect a state-machine transition on the icon."""
        try:
            self.icon.icon = _state_image(state)
            self.icon.title = f"Dictate — {state.lower()}"
        except Exception:
            logger.debug("Icon update failed", exc_info=True)

    def _on_record(self, _icon, _item) -> None:
        logger.info("Tray: record button clicked")
        try:
            self.app.toggle_recording()
        except Exception:
            logger.exception("Tray record button failed")

    def _on_open_config(self, _icon, _item) -> None:
        save_config(self.app.config, self.config_path)
        os.startfile(str(self.config_path))  # noqa: S606

    def _on_reload(self, _icon, _item) -> None:
        self.app.reload_config()

    def _on_exit(self, _icon, _item) -> None:
        logger.info("Exit requested from tray")
        self.icon.stop()
        self.stop_event.set()


def run_with_tray(app: DictationApp) -> None:
    """Start the tray UI and the app loop; return when the user exits."""
    tray = TrayUI(app)
    tray.start()
    app.run_forever(tray.stop_event)


