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
ICON_FILE = Path(__file__).parent.parent / "assets" / "dictate.ico"

STATUS_LABELS = {
    "IDLE": "Pripravený",
    "RECORDING": "Nahrávam",
    "TRANSCRIBING": "Prepisujem",
    "INJECTING": "Vkladám",
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

    # The page is laid out at these CSS pixels. Physical size is this times the DPI scale of the
    # monitor the window is actually on, which is not always the system's.
    LOGICAL_SIZE = (144, 45)
    CSS_RADIUS = 0           # must equal border-radius on .pill in ui/index.html

    @staticmethod
    def _window_size() -> tuple[int, int]:
        """Return the window size in physical pixels for the SYSTEM scaling.

        Only used for the initial create_window call. `_force_size` sets the real size from the
        window's own monitor, because GetDpiForSystem reports the primary display: here it says
        96 while the window sits on a 144 dpi screen, and the window came out at two thirds size.
        """
        import ctypes

        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            dpi = int(user32.GetDpiForSystem())
        except Exception:
            dpi = 96
        scale = dpi / 96
        # The window shows one thing: that the microphone is hearing you. The hotkey starts and
        # stops the run, and config, reload and exit are in the tray, so the status line, the
        # transcript and the two title-bar buttons all went. What is left is a mark and a meter.
        #
        # The height is the 25 px mark plus 2 px of margin above and below plus the pill's own
        # 1 px border, so 31. Measured from the rendered page rather than added up by hand.
        # The meter is 93 px against the 140 it started with, a third off.
        return round(144 * scale), round(31 * scale)

    def _force_size(self) -> None:
        """Set the window to the exact pixel size, over pywebview's own arithmetic.

        MEASURED, because three rounds of changing the requested height changed nothing on
        screen. On this display pywebview maps a request to `1.5 * asked - 22` wide and
        `1.5 * asked - 56` tall, an exact fit over three probe sizes: (144,31) became (194,1),
        (216,46) became (302,13) and (300,120) became (428,124). The 1.5 is the DPI scale; the
        subtractions are window-frame insets on a window that has no frame. Asking for 31 px of
        height therefore asked for a negative number and got whatever the minimum was.

        So the size is set on the real window handle instead. Win32 takes physical pixels and
        applies no arithmetic of its own.
        """
        import ctypes

        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        user32 = ctypes.windll.user32
        hwnd = 0
        for _ in range(120):                       # the window appears a moment after start()
            hwnd = user32.FindWindowW(None, "Dictate")
            if hwnd or self.stop_event.wait(0.1):
                break
        if not hwnd:
            logger.warning("Never found the window to size it; it keeps pywebview's own size")
            return

        dpi = int(user32.GetDpiForWindow(hwnd)) or 96
        scale = dpi / 96
        want_w = round(self.LOGICAL_SIZE[0] * scale)
        want_h = round(self.LOGICAL_SIZE[1] * scale)
        SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE = 0x0002, 0x0004, 0x0010

        # SET, THEN READ BACK, AND REPEAT UNTIL IT STICKS. The first version set the size once and
        # logged success: it really did call SetWindowPos with 216x46, and the window measured
        # 144x31 a moment later, because pywebview applies its own size after the window appears.
        # A log line saying what was asked for is not a measurement of what happened.
        rect = RECT()
        for attempt in range(40):
            user32.SetWindowPos(hwnd, 0, 0, 0, want_w, want_h,
                                SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE)
            if self.stop_event.wait(0.15):
                return
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            got = (rect.right - rect.left, rect.bottom - rect.top)
            if got == (want_w, want_h):
                logger.info("Window settled at %dx%d physical (%dx%d css at %d dpi) after %d tries",
                            got[0], got[1], *self.LOGICAL_SIZE, dpi, attempt + 1)
                return
        logger.warning("Window will not hold %dx%d; it sits at %dx%d", want_w, want_h, *got)

    def _round_corners(self, hwnd: int, width: int, height: int, scale: float) -> None:
        """Clip the window itself to the pill's outline.

        The page draws a rounded rectangle; the window around it is a square. At the corners the
        square showed through, which reads as a second frame around the app rather than as the
        app's own edge lighting up. Clipping the window to the same radius makes the glowing
        border the window's actual silhouette, so there is one outline and it is the one that
        pulses.

        The radius here must track `border-radius` in the stylesheet. They are the same shape
        described twice, and if they drift the corners either clip the border or leave a sliver
        of square behind it.
        """
        import ctypes

        radius = round(self.CSS_RADIUS * scale)
        rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1,
                                                     radius * 2, radius * 2)
        if not rgn:
            logger.debug("CreateRoundRectRgn failed; the window keeps square corners")
            return
        ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)

    def run(self) -> None:
        """Open the pill window and block until the user exits."""
        import ctypes

        try:
            # Per-monitor DPI awareness: crisp rendering and correct CSS
            # viewport size on displays scaled above 100%.
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            logger.debug("SetProcessDpiAwareness failed", exc_info=True)
        try:
            # Without its own AppUserModelID the taskbar files this window under pythonw.exe and
            # shows the Python logo, which is the multicoloured icon the owner saw.
            shell32 = ctypes.WinDLL("shell32", use_last_error=True)
            shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
            shell32.SetCurrentProcessExplicitAppUserModelID("Agora.Dictate")
        except Exception:
            logger.debug("SetCurrentProcessExplicitAppUserModelID failed", exc_info=True)
        threading.Thread(target=self._track_foreground, daemon=True).start()
        threading.Thread(target=self._force_size, daemon=True).start()
        width, height = self._window_size()
        self._window = webview.create_window(
            "Dictate",
            str(UI_FILE),
            js_api=self,
            width=width,
            height=height,
            # THE HEIGHT WAS NEVER APPLIED. pywebview's min_size defaults to (200, 100) and clamps
            # anything smaller, so three rounds of cutting the CSS and the requested height changed
            # nothing: the live window measured 201x100 physical while 216x46 was being asked for.
            # Found by reading the window rect off the running window instead of trusting the call.
            min_size=(1, 1),
            frameless=True,
            on_top=True,
            easy_drag=False,
            background_color="#0b0b0c",
            transparent=False,
            resizable=False,
        )
        if ICON_FILE.exists():
            webview.start(icon=str(ICON_FILE))
        else:
            logger.warning("Window icon missing at %s; the taskbar will fall back to "
                           "the interpreter's own icon", ICON_FILE)
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

