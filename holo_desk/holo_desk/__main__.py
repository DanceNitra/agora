"""Start Yuki: a frameless, transparent, always-on-top window on the desktop.

Hotkeys:
  Ctrl+Alt+Space  talk without saying "Yuki"
  Ctrl+Alt+Y      close or open her eyes (the screenshot sent with each question)
  Ctrl+Alt+H      hide or show the text under her
  Ctrl+Alt+M      switch every question to Opus 5.5 (smart, about 4 s) or back to Haiku 5.5
                  (fast, default). "porozmýšľaj" sends one question to Opus.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path

import webview

from .keys import anthropic_key

WEB = Path(__file__).resolve().parent.parent / "web" / "index.html"
LOG = Path(os.path.expandvars(r"%LOCALAPPDATA%\HoloDesk\holo_desk.log"))


def _single_instance() -> bool:
    """One Yuki at a time: a pid file, checked against the running processes."""
    pid_file = LOG.with_name("holo_desk.pid")
    try:
        old = int(pid_file.read_text())
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, old)   # QUERY_LIMITED_INFORMATION
        if handle:
            code = ctypes.c_ulong()
            ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            ctypes.windll.kernel32.CloseHandle(handle)
            if code.value == 259:   # STILL_ACTIVE
                return False
    except (OSError, ValueError):
        pass
    pid_file.write_text(str(os.getpid()))
    return True


class Api:
    """Methods the page may call."""

    def __init__(self) -> None:
        self.ready_event = threading.Event()
        self.clips: list[str] = []

    def ready(self, clips):
        self.clips = list(clips)
        self.ready_event.set()


def main() -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(LOG, encoding="utf-8")]
    if sys.stdout:   # pythonw (the desktop icon) has no console
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=handlers)
    # 2026-11-13 Yuki vanished at 10:49 with nothing in the log or the event log. From now on a
    # native crash dumps a stack into the log, and a normal exit says so.
    import atexit
    import faulthandler

    crash = open(LOG.with_name("holo_desk_crash.log"), "a", encoding="utf-8")
    faulthandler.enable(crash)
    atexit.register(lambda: logging.info("Exit (window closed or normal end)"))
    if not _single_instance():
        logging.info("Yuki is already running; not starting a second one")
        return
    logging.info("Start, pid %d", os.getpid())
    key = anthropic_key()
    if not key:
        print("No Anthropic key, Yuki cannot think. Run again and paste the key.")
        return
    if not WEB.with_name("nova.glb").is_file():
        print(f"Missing {WEB.with_name('nova.glb')}: copy the character there.")
        return

    api = Api()
    window = webview.create_window("Yuki", url=str(WEB), js_api=api, width=380, height=680,
                                   frameless=True, on_top=True, easy_drag=True,
                                   background_color="#000000")
    hidden = {"status": False}

    def boot():
        from .app import Yuki

        api.ready_event.wait(30)
        logging.info("Clips: %s", api.clips)
        yuki = Yuki(window, key)
        try:
            import keyboard

            keyboard.add_hotkey("ctrl+alt+space", yuki.listen_now)
            keyboard.add_hotkey("ctrl+alt+y", yuki.toggle_eyes)
            keyboard.add_hotkey("ctrl+alt+m", yuki.toggle_model)

            def toggle_text():
                hidden["status"] = not hidden["status"]
                yuki.js(f"window.yuki.hideStatus({str(hidden['status']).lower()})")

            keyboard.add_hotkey("ctrl+alt+h", toggle_text)
        except Exception:
            logging.exception("Hotkeys unavailable")
        yuki.start()

    webview.start(boot, gui="edgechromium", http_server=True)


if __name__ == "__main__":
    main()
