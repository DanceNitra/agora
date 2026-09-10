"""First-run setup: check the GPU, download the models, pick a microphone, show the keys.

The installer runs this once after copying the program files. It is Tkinter rather than
the app's own WebView window because it has to run before anything is provisioned, and
Tkinter is already inside the Python runtime the app ships.

Four pages, in order:

1. System check. An NVIDIA GPU is required, so this page can stop the setup.
2. Download. Whisper and the Silero voice detector, with a progress bar, then a
   transcription of a bundled clip that proves the GPU was really used.
3. Microphone. Every input device the system reports, with a live level bar.
4. How it works. The keys, the states, and how to close the app, which has no title bar.

No CUDA runtime is downloaded. CTranslate2's Windows build carries what it needs; the
packaged app was measured transcribing on the GPU with every CUDA directory removed from
PATH, so the only outside requirement is the NVIDIA driver.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .config import default_config_path

logger = logging.getLogger(__name__)

BG = "#0f1116"
FG = "#e8e8ee"
DIM = "#9a9aa8"
ACCENT = "#2bf4ff"
BAD = "#ff6b6b"


class SetupWizard:
    """A four-page setup window."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path
        self.root = tk.Tk()
        self.root.title("Dictate setup")
        self.root.configure(bg=BG)
        self.root.geometry("640x420")
        self.root.resizable(False, False)
        try:
            icon = Path(__file__).parent.parent / "assets" / "dictate.ico"
            if icon.exists():
                self.root.iconbitmap(str(icon))
        except tk.TclError:
            logger.debug("icon not applied", exc_info=True)

        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", expand=True, padx=28, pady=(24, 8))

        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=28, pady=(0, 20))
        self.status = tk.Label(footer, text="", bg=BG, fg=DIM, anchor="w",
                               font=("Segoe UI", 9))
        self.status.pack(side="left")
        self.next_button = tk.Button(footer, text="Next", width=12, command=self._next,
                                     bg="#1b1e26", fg=FG, activebackground="#252935",
                                     activeforeground=FG, relief="flat",
                                     font=("Segoe UI", 10))
        self.next_button.pack(side="right")

        self.page = 0
        self.gpu_ok = False
        self.mic_index: int | None = None
        self._queue: queue.Queue = queue.Queue()
        self._meter_stream = None
        self._render()

    # -- shared widgets --------------------------------------------------------

    def _clear(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()

    def _title(self, text: str, subtitle: str = "") -> None:
        tk.Label(self.body, text=text, bg=BG, fg=FG, anchor="w",
                 font=("Segoe UI Semibold", 16)).pack(fill="x")
        if subtitle:
            tk.Label(self.body, text=subtitle, bg=BG, fg=DIM, anchor="w", justify="left",
                     wraplength=580, font=("Segoe UI", 10)).pack(fill="x", pady=(6, 16))
        else:
            tk.Frame(self.body, bg=BG, height=16).pack()

    def _line(self, text: str, colour: str = FG, size: int = 10) -> tk.Label:
        label = tk.Label(self.body, text=text, bg=BG, fg=colour, anchor="w",
                         justify="left", wraplength=580, font=("Segoe UI", size))
        label.pack(fill="x", pady=2)
        return label

    # -- page 1: system check --------------------------------------------------

    def _page_system(self) -> None:
        self._title(
            "System check",
            "Dictate transcribes with Whisper on the graphics card. Everything below has "
            "to pass before the model is worth downloading.")
        from .preflight import WEBVIEW2_URL, run_all

        results = run_all()
        self.gpu_ok = all(ok for _, ok, _ in results)
        for label, ok, detail in results:
            self._line("%s%s: %s" % ("" if ok else "PROBLEM  ", label, detail),
                       ACCENT if ok else BAD, 10)
        if self.gpu_ok:
            self.status.config(text="")
            self.next_button.config(state="normal")
            return

        self.next_button.config(state="disabled")
        self.status.config(text="Fix the lines marked PROBLEM, then run the setup again.")
        if not dict((label, ok) for label, ok, _ in results).get("WebView2 runtime", True):
            self._line("", DIM)
            self._line(WEBVIEW2_URL, ACCENT, 10)

    # -- page 2: download ------------------------------------------------------

    def _page_download(self) -> None:
        self._title("Downloading the model",
                    "Whisper large-v3-turbo and the Silero voice detector, about 1.6 GB. "
                    "They go into your user profile, so this runs once. Afterwards the "
                    "setup transcribes a short clip to prove the GPU is being used.")
        self.progress = ttk.Progressbar(self.body, mode="determinate", maximum=1000)
        self.progress.pack(fill="x", pady=(8, 10))
        self.detail = self._line("Starting...", DIM)
        self.next_button.config(state="disabled")
        threading.Thread(target=self._download, daemon=True).start()
        self.root.after(100, self._drain)

    def _download(self) -> None:
        try:
            from .asr import models

            if models.is_model_installed() and models.is_vad_installed():
                self._queue.put(("detail", "The model is already installed."))
                self._queue.put(("progress", (0.5, "Checking the GPU...")))
            else:
                # Report bytes, not a spinner. On a second machine this page looked hung
                # for the whole download, because the bar only moved once it finished.
                last = [0.0]

                def report(progress) -> None:
                    now = time.monotonic()
                    if now - last[0] < 0.2 and progress.done < progress.total:
                        return
                    last[0] = now
                    left = progress.seconds_left
                    eta = ("%d min %02d s" % divmod(int(left), 60)) if left else "..."
                    self._queue.put(("progress", (
                        progress.fraction * 0.5,
                        "%s: %.0f of %.0f MB  ·  %.1f MB/s  ·  %s left"
                        % (progress.file, progress.done / 1e6, progress.total / 1e6,
                           progress.bytes_per_second / 1e6, eta))))

                self._queue.put(("detail", "Downloading Whisper large-v3-turbo, 1.6 GB"))
                models.download_model(progress_callback=report)
                self._queue.put(("progress", (0.5, "Model installed. Checking the GPU...")))

            # The self-test is the acceptance criterion, not the download. CTranslate2
            # runs on the CPU without complaining when CUDA is unavailable, and this
            # model on the CPU returns noise, so an install is not finished until a real
            # transcription has come back off the GPU.
            from .cli import run_selftest

            code, report = run_selftest(self.config_path)
            if code == 0:
                self._queue.put(("done", "Running on the %s at %.0f seconds of audio "
                                 "per second of work."
                                 % (report["device"], 1 / max(report["rtf"], 1e-6))))
            else:
                self._queue.put(("error", report["failure"]))
        except Exception as exc:                       # surfaced on the page, not hidden
            logger.exception("setup download failed")
            self._queue.put(("error", f"{type(exc).__name__}: {exc}"))

    def _drain(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "detail":
                    self.detail.config(text=payload, fg=DIM)
                elif kind == "progress":
                    fraction, what = payload
                    self.progress["value"] = max(0, min(1000, int(fraction * 1000)))
                    self.detail.config(text=what, fg=DIM)
                elif kind == "done":
                    self.progress["value"] = 1000
                    self.detail.config(text=payload or "Everything is installed.",
                                       fg=ACCENT)
                    self.next_button.config(state="normal")
                    return
                elif kind == "error":
                    self.detail.config(text=payload, fg=BAD)
                    self.status.config(text="Close the setup and run it again to retry.")
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._drain)

    # -- page 3: microphone ----------------------------------------------------

    def _page_microphone(self) -> None:
        self._title("Microphone",
                    "Pick the microphone Dictate listens to. Speak: the bar shows what "
                    "the selected device hears.")
        import sounddevice as sd

        devices = sd.query_devices()
        self.inputs = [(i, d) for i, d in enumerate(devices) if d["max_input_channels"] > 0]
        names = [
            f"[{i}] {d['name']} ({sd.query_hostapis(d['hostapi'])['name']})"
            for i, d in self.inputs
        ]
        default_index = 0
        for position, (index, _) in enumerate(self.inputs):
            if index == sd.default.device[0]:
                default_index = position

        self.choice = ttk.Combobox(self.body, values=names, state="readonly", width=70)
        self.choice.current(default_index if names else 0)
        self.choice.pack(fill="x", pady=(4, 12))
        self.choice.bind("<<ComboboxSelected>>", lambda _event: self._restart_meter())

        self.level = ttk.Progressbar(self.body, mode="determinate", maximum=1000)
        self.level.pack(fill="x")
        self.level_text = self._line("Listening...", DIM)
        self._restart_meter()

    def _restart_meter(self) -> None:
        """Open a stream on the selected device and drive the level bar from it."""
        import numpy as np
        import sounddevice as sd

        if self._meter_stream is not None:
            try:
                self._meter_stream.close()
            except Exception:
                logger.debug("meter close failed", exc_info=True)
            self._meter_stream = None
        if not self.inputs:
            self.level_text.config(text="No input device found.", fg=BAD)
            return
        index = self.inputs[self.choice.current()][0]
        self.mic_index = index

        def callback(indata, _frames, _time, _status):
            peak = float(np.max(np.abs(indata))) if indata.size else 0.0
            self._queue.put(("level", peak))

        try:
            self._meter_stream = sd.InputStream(device=index, channels=1, callback=callback)
            self._meter_stream.start()
            self.level_text.config(text="Speak to test this microphone.", fg=DIM)
        except Exception as exc:
            self.level_text.config(text=f"This device did not open: {exc}", fg=BAD)
        self.root.after(60, self._drain_level)

    def _drain_level(self) -> None:
        if self.page != 2:
            return
        peak = None
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "level":
                    peak = payload
        except queue.Empty:
            pass
        if peak is not None:
            self.level["value"] = min(1000, int(peak * 2000))
        self.root.after(60, self._drain_level)

    def _save_microphone(self) -> None:
        from .config import load_config, save_config

        if self._meter_stream is not None:
            try:
                self._meter_stream.close()
            except Exception:
                logger.debug("meter close failed", exc_info=True)
            self._meter_stream = None
        config = load_config(self.config_path)
        config.microphone = self.mic_index
        save_config(config, self.config_path)
        logger.info("Microphone set to device %s", self.mic_index)

    # -- page 4: how it works --------------------------------------------------

    def _page_help(self) -> None:
        from .config import load_config

        # Read the key from the config rather than writing it into the sentence. It was
        # hardcoded here as Ctrl+Shift+R while the app listened on right Ctrl, so the
        # page taught the wrong key with complete confidence.
        hotkey = load_config(self.config_path).hotkey
        pretty = " + ".join(part.strip().title() for part in hotkey.split("+"))

        self._title("How it works", "")
        for text, colour in (
            ("Hold %s and speak. Release it to transcribe." % pretty, FG),
            ("While the microphone is open the window's edge glows cyan.", DIM),
            ("Then it shows TRANSCRIBING and PASTING while the model runs.", DIM),
            ("The text is pasted into whatever window you were in before.", DIM),
            ("", DIM),
            ("The window has no close button.", FG),
            ("To close Dictate, right-click its icon on the taskbar at the bottom of the "
             "screen and choose Close window. The tray icon next to the clock has the "
             "same Exit item.", DIM),
            ("", DIM),
            ("To move the window, drag it. It stays on top of other windows.", DIM),
            ("To change the key, edit %s." % (default_config_path()), DIM),
        ):
            self._line(text, colour)
        self.next_button.config(text="Finish")

    # -- flow ------------------------------------------------------------------

    PAGES = ("_page_system", "_page_download", "_page_microphone", "_page_help")

    def _render(self) -> None:
        self._clear()
        self.next_button.config(text="Next")
        getattr(self, self.PAGES[self.page])()

    def _next(self) -> None:
        if self.page == 2:
            self._save_microphone()
        if self.page == len(self.PAGES) - 1:
            self.root.destroy()
            return
        self.page += 1
        self._render()

    def run(self) -> int:
        """Show the wizard and return 0 when it closes."""
        self.root.mainloop()
        return 0


def main(config_path: Path | None = None, page: int = 0) -> int:
    """Run the setup wizard, optionally opening straight at one page."""
    from .log import setup_logging

    setup_logging("INFO")
    wizard = SetupWizard(config_path)
    if page:
        # The Start menu has a "How Dictate works" shortcut that opens the last page on
        # its own, so the instructions are readable after setup rather than only during.
        wizard.page = page
        wizard._render()
    return wizard.run()


if __name__ == "__main__":
    import sys

    raise SystemExit(main(page=3 if "--help-page" in sys.argv else 0))
