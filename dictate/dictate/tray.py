"""System tray icon with states and a settings menu.

The icon is the app's logo, tinted by state: amber at rest, red while the
microphone is open, off-white while the model runs. It is the same mark the
overlay and the taskbar icon use, so the app looks like one thing everywhere.

The colour lives here and the shape lives in ``assets/mark_mask.png``, an
alpha-only master. Baking a picture per state would have put the palette in
four files.

The menu carries the record button, "Open config" (plain JSON file), reload,
and exit. Those left the overlay window, which now shows only the meter.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from .app import IDLE, RECORDING, DictationApp
from .config import default_config_path, save_config

logger = logging.getLogger(__name__)

STATE_COLORS = {
    "IDLE": (232, 163, 60),          # amber, the app's accent
    "RECORDING": (216, 67, 75),      # the tally red the overlay uses
    "TRANSCRIBING": (232, 230, 225),
    "INJECTING": (232, 230, 225),
}

MASK_PATH = Path(__file__).parent.parent / "assets" / "mark_mask.png"
_MASK: Image.Image | None = None


def _mask() -> Image.Image | None:
    """Load the alpha-only logo once, or None if it is missing."""
    global _MASK
    if _MASK is None and MASK_PATH.exists():
        _MASK = Image.open(MASK_PATH).convert("RGBA").resize((64, 64), Image.LANCZOS)
    return _MASK


def _state_image(state: str) -> Image.Image:
    """Return the logo tinted for the state.

    Falls back to a filled circle if the mask is missing, because a tray icon that
    fails to load should still tell you which state the app is in.
    """
    color = STATE_COLORS.get(state, STATE_COLORS["IDLE"])
    mask = _mask()
    if mask is None:
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse((8, 8, 56, 56), fill=color)
        return image
    tinted = Image.new("RGBA", mask.size, color + (255,))
    tinted.putalpha(mask.getchannel("A"))
    return tinted


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


