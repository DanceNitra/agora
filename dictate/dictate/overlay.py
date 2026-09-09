"""Standalone dictation window: oscilloscope meter, transcript, buttons.

Runs tkinter in the thread that constructed the window (normally the
main thread). The window tracks the last external foreground window so
the paste can return focus to the application the user was working in.
"""

from __future__ import annotations

import logging
import queue
import tkinter as tk

from .app import IDLE
from .inject import focus

logger = logging.getLogger(__name__)

WIDTH = 420
HEIGHT = 286
SCOPE_W = 392
SCOPE_H = 108
HISTORY = 392  # one envelope point per pixel

BG = "#0F1117"
PANEL = "#161922"
LINE = "#2A2E3C"
FG = "#E6E6F0"
MUTED = "#8A8A98"
GREEN = "#4CAF50"
RED = "#FF5252"
AMBER = "#FFB74D"


class ControlWindow:
    """Small always-on-top dictation HUD with an oscilloscope."""

    def __init__(self, on_toggle=None, stop_event=None, app=None) -> None:
        self.on_toggle = on_toggle
        self.stop_event = stop_event
        self.app = app
        self.last_external = 0
        self._commands: queue.Queue[tuple[str, object]] = queue.Queue()
        self._wave: list[float] = []
        self._state = IDLE
        self._tick = 0

    # -- thread-safe API -----------------------------------------------------

    def set_state(self, state: str) -> None:
        """Reflect an app state change (thread-safe)."""
        self._commands.put(("state", state))

    def set_level(self, peak: float) -> None:
        """Push a new microphone peak level (thread-safe)."""
        self._commands.put(("level", float(peak)))

    def set_wave(self, envelope: list[float]) -> None:
        """Push a batch of waveform envelope points (thread-safe)."""
        self._commands.put(("wave", envelope))

    def set_transcript(self, text: str) -> None:
        """Show the last transcript (thread-safe)."""
        self._commands.put(("text", text))

    def run(self) -> None:
        """Build the window and block in the Tk mainloop."""
        self.root = tk.Tk()
        self.root.title("Dictate")
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        x = (self.root.winfo_screenwidth() - WIDTH) // 2
        self.root.geometry(f"{WIDTH}x{HEIGHT}+{x}+30")

        self.canvas = tk.Canvas(
            self.root,
            width=SCOPE_W,
            height=SCOPE_H,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=LINE,
        )
        self.canvas.pack(padx=14, pady=(12, 6))
        # static grid
        for gy in (SCOPE_H // 4, SCOPE_H // 2, 3 * SCOPE_H // 4):
            self.canvas.create_line(0, gy, SCOPE_W, gy, fill=LINE, dash=(2, 6))

        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="x", padx=14, pady=(4, 0))

        self.status = tk.Label(
            row, text="PRIPRAVENÝ", bg=BG, fg=MUTED,
            font=("Segoe UI", 11, "bold"), anchor="w",
        )
        self.status.pack(side="left", fill="x", expand=True)

        self.toggle_btn = tk.Button(
            row,
            text="●  RECORD",
            command=self._on_toggle,
            bg="#2E7D32", fg="white",
            activebackground="#388E3C", activeforeground="white",
            relief="flat", bd=0,
            font=("Segoe UI", 11, "bold"), padx=18, pady=6,
            cursor="hand2",
        )
        self.toggle_btn.pack(side="right")

        self.transcript = tk.Label(
            self.root, text="", bg=PANEL, fg=FG,
            font=("Segoe UI", 9), anchor="w", justify="left",
            wraplength=WIDTH - 36, padx=8, pady=6,
        )
        self.transcript.pack(fill="x", padx=14, pady=(8, 4))

        tools = tk.Frame(self.root, bg=BG)
        tools.pack(fill="x", padx=14, pady=(2, 10))
        tk.Button(
            tools, text="Open config", command=self._open_config,
            bg="#1B1E28", fg=MUTED, activebackground="#262A38",
            activeforeground=FG, relief="flat", bd=0, font=("Segoe UI", 9),
            cursor="hand2",
        ).pack(side="left")
        tk.Button(
            tools, text="Exit", command=self._exit,
            bg="#1B1E28", fg=MUTED, activebackground="#4A2430",
            relief="flat", bd=0, font=("Segoe UI", 9), cursor="hand2",
        ).pack(side="right")

        self.root.after(40, self._poll)
        self.root.mainloop()

    def quit(self) -> None:
        """Close the window (thread-safe)."""
        self._commands.put(("quit", None))

    # -- internals -------------------------------------------------------------

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
                    self._push_level(float(value))
                elif cmd == "wave":
                    self._wave.extend(value)
                    excess = len(self._wave) - HISTORY
                    if excess > 0:
                        self._wave = self._wave[excess:]
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

        self._tick += 1
        if self._tick % 2 == 0:  # ~80 ms: track the paste target
            hwnd = focus.get_foreground_window()
            if focus.is_external_window(hwnd):
                self.last_external = hwnd

        self._draw()
        self.root.after(40, self._poll)

    def _push_level(self, peak: float) -> None:
        """A level without envelope data still advances the trace."""
        self._wave.append(peak)
        excess = len(self._wave) - HISTORY
        if excess > 0:
            self._wave = self._wave[excess:]

    def _apply_state(self, state: str) -> None:
        self._state = state
        if state == "RECORDING":
            self.status.configure(text="NAHRÁVAM", fg=RED)
            self.toggle_btn.configure(text="■  STOP", bg="#C62828", activebackground="#D32F2F")
        elif state in ("TRANSCRIBING", "INJECTING"):
            self.status.configure(text="PREPISUJEM…", fg=AMBER)
            self.toggle_btn.configure(state="disabled")
        else:
            self.status.configure(text="PRIPRAVENÝ", fg=MUTED)
            self.toggle_btn.configure(
                text="●  RECORD", bg="#2E7D32", activebackground="#388E3C"
            )
            self.toggle_btn.configure(state="normal")

    def _draw(self) -> None:
        self.canvas.delete("wave")
        n = len(self._wave)
        if n < 2:
            return
        points: list[float] = []
        step_x = SCOPE_W / (HISTORY - 1)
        start_index = max(0, n - HISTORY)
        for i, value in enumerate(self._wave[start_index:]):
            x = (start_index + i) * step_x
            y = SCOPE_H / 2 - max(1.0, min(1.0, value)) * (SCOPE_H / 2 - 4)
            points.extend((x, y))
        if len(points) >= 4:
            self.canvas.create_line(
                *points, fill=GREEN, width=2, tags="wave", smooth=True
            )
            # soft baseline dot at the writing head
            self.canvas.create_oval(
                points[-2] - 2, points[-1] - 2,
                points[-2] + 2, points[-1] + 2,
                fill=RED, outline="", tags="wave",
            )

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
