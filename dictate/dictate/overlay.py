"""Standalone desktop dictation window: button, live waveform, transcript.

Runs tkinter in the thread that constructed the window (normally the
main thread). The window tracks the last external foreground window so
the paste can return focus to the application the user was working in,
even though clicking this window (or the tray) stole focus.
"""

from __future__ import annotations

import logging
import queue
import tkinter as tk

from .app import IDLE, RECORDING
from .inject import focus

logger = logging.getLogger(__name__)

WIDTH = 380
HEIGHT = 210
BARS = 60
BAR_W = 4
BAR_GAP = 2
PAD = 16


class ControlWindow:
    """Small always-on-top dictation HUD."""

    def __init__(self, on_toggle=None, stop_event=None, app=None) -> None:
        self.on_toggle = on_toggle
        self.stop_event = stop_event
        self.app = app
        self.last_external = 0
        self._commands: queue.Queue[tuple[str, object]] = queue.Queue()
        self._levels: list[float] = [0.0] * BARS
        self._smooth: list[float] = [0.0] * BARS
        self._state = IDLE
        self._tick = 0

    # -- thread-safe API ----------------------------------------------------

    def set_state(self, state: str) -> None:
        """Reflect an app state change (thread-safe)."""
        self._commands.put(("state", state))

    def set_level(self, peak: float) -> None:
        """Push a new microphone level (thread-safe)."""
        self._commands.put(("level", float(peak)))

    def set_transcript(self, text: str) -> None:
        """Show the last transcript (thread-safe)."""
        self._commands.put(("text", text))

    def run(self) -> None:
        """Build the window and block in the Tk mainloop."""
        self.root = tk.Tk()
        self.root.title("Dictate")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#14141B")
        self.root.resizable(False, False)

        x = (self.root.winfo_screenwidth() - WIDTH) // 2
        self.root.geometry(f"{WIDTH}x{HEIGHT}+{x}+40")

        self.canvas = tk.Canvas(
            self.root,
            width=WIDTH - 24,
            height=64,
            bg="#0F0F16",
            highlightthickness=1,
            highlightbackground="#2A2A38",
        )
        self.canvas.pack(padx=12, pady=(10, 4))

        row = tk.Frame(self.root, bg="#14141B")
        row.pack(fill="x", padx=12)

        self.status = tk.Label(
            row, text="PRIPRAVENÝ", bg="#14141B", fg="#8A8A98",
            font=("Segoe UI", 10, "bold"), anchor="w",
        )
        self.status.pack(side="left", fill="x", expand=True)

        self.toggle_btn = tk.Button(
            row,
            text="●  RECORD",
            command=self._on_toggle,
            bg="#2E7D32", fg="white",
            activebackground="#388E3C", activeforeground="white",
            relief="flat", bd=0,
            font=("Segoe UI", 10, "bold"), padx=14, pady=4,
        )
        self.toggle_btn.pack(side="right")

        self.transcript = tk.Label(
            self.root, text="", bg="#14141B", fg="#C9C9D6",
            font=("Segoe UI", 9), anchor="w", justify="left", wraplength=WIDTH - 28,
        )
        self.transcript.pack(fill="x", padx=14, pady=(2, 8))

        tools = tk.Frame(self.root, bg="#14141B")
        tools.pack(fill="x", padx=12, pady=(0, 8))
        tk.Button(
            tools, text="Open config", command=self._open_config,
            bg="#24242E", fg="#B9B9C6", activebackground="#33333F",
            relief="flat", bd=0, font=("Segoe UI", 8),
        ).pack(side="left")
        tk.Button(
            tools, text="Exit", command=self._exit,
            bg="#24242E", fg="#B9B9C6", activebackground="#5A2A2A",
            relief="flat", bd=0, font=("Segoe UI", 8),
        ).pack(side="right")

        self.root.after(50, self._poll)
        self.root.mainloop()

    def quit(self) -> None:
        """Close the window (thread-safe)."""
        self._commands.put(("quit", None))

    # -- internals ------------------------------------------------------------

    def _on_toggle(self) -> None:
        logger.info("Window: record button clicked")
        if self.on_toggle is not None:
            self.on_toggle()

    def _poll(self) -> None:
        try:
            while True:
                cmd, value = self._commands.get_nowait()
                if cmd == "state":
                    self._apply_state(str(value))
                elif cmd == "level":
                    self._levels.append(float(value))
                    self._levels.pop(0)
                elif cmd == "text":
                    self.transcript.configure(text=str(value))
                elif cmd == "quit":
                    self.root.quit()
                    return
        except queue.Empty:
            pass

        if self.stop_event is not None and self.stop_event.is_set():
            self.root.quit()
            return

        # Track the last external foreground window for the paste target.
        self._tick += 1
        if self._tick % 2 == 0:  # every ~100 ms
            hwnd = focus.get_foreground_window()
            if focus.is_external_window(hwnd):
                self.last_external = hwnd

        self._draw()
        self.root.after(50, self._poll)

    def _apply_state(self, state: str) -> None:
        self._state = state
        if state == RECORDING:
            self.status.configure(text="NAHRÁVAM", fg="#FF5252")
            self.toggle_btn.configure(text="■  STOP", bg="#C62828", activebackground="#D32F2F")
        elif state in ("TRANSCRIBING", "INJECTING"):
            self.status.configure(text="PREPISUJEM…", fg="#FFB74D")
            self.toggle_btn.configure(state="disabled")
        else:
            self.status.configure(text="PRIPRAVENÝ", fg="#8A8A98")
            self.toggle_btn.configure(text="●  RECORD", bg="#2E7D32", activebackground="#388E3C")
            self.toggle_btn.configure(state="normal")

    def _draw(self) -> None:
        self.canvas.delete("wave")
        step = BAR_W + BAR_GAP
        for index, target in enumerate(self._levels):
            smooth_prev = getattr(self, "_smooth", None)
            if smooth_prev is None:
                self._smooth = [0.0] * BARS
            self._smooth[index] = self._smooth[index] + (target - self._smooth[index]) * 0.35
            height = max(3, min(1.0, self._smooth[index]) * 56)
            x = PAD + index * step
            y0 = 32 - height / 2
            y1 = 32 + height / 2
            self.canvas.create_rectangle(
                x, y0, x + BAR_W, y1, fill=self._color_for(self._smooth[index]),
                outline="", tags="wave",
            )

    def _color_for(self, level: float) -> str:
        if level < 0.15:
            return "#4CAF50"
        if level < 0.45:
            return "#FFC107"
        return "#FF5252"

    def _open_config(self) -> None:
        import os

        from .config import default_config_path, save_config

        path = default_config_path()
        if self.app is not None:
            save_config(self.app.config, path)
        os.startfile(str(path))  # noqa: S606

    def _exit(self) -> None:
        if self.stop_event is not None:
            self.stop_event.set()
        self.root.quit()

