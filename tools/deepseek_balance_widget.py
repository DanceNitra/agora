# -*- coding: utf-8 -*-
"""deepseek_balance_widget.py - the DeepSeek balance, anchored inside the Codex sidebar footer.

A borderless label sits in the empty space of the Codex settings row (bottom left, beside the
"deepseek" profile name), follows the Codex window when it moves or resizes, and hides whenever
Codex is minimized or another app is in front. The balance refreshes every 60 s; the spend over
the last 10 minutes appears once 10 minutes of readings exist. Under 0.50 USD the text turns red.
Codex's notify toast only fires when a turn ENDS; this view updates while a turn runs.

    pythonw tools\\deepseek_balance_widget.py        (also started from the Windows Startup folder)
"""
import collections
import ctypes
import os
import ctypes.wintypes as W
import json
import threading
import time
import tkinter as tk

from deepseek_balance_notify import LOG, balance

REFRESH_S = 60
WARN_USD = 0.50
BG = "#1b1b1b"            # the Codex sidebar footer colour, sampled from a screenshot
FG, FG_WARN = "#8f8f8f", "#ff6b6b"
# Position inside the Codex window, in the same (DPI-virtualised) units GetWindowRect returns.
X_FROM_LEFT = 112          # just right of the "deepseek" profile name
Y_FROM_BOTTOM = 21         # vertically centred on the settings row
CODEX_TITLE = "ChatGPT"    # the Codex desktop app's window title

user32 = ctypes.windll.user32


def codex_window():
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, W.HWND, W.LPARAM)
    def cb(h, _):
        n = user32.GetWindowTextLengthW(h)
        if n and user32.IsWindowVisible(h):
            b = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(h, b, n + 1)
            if b.value == CODEX_TITLE:
                found.append(h)
        return True

    user32.EnumWindows(cb, 0)
    return found[0] if found else None


class Widget:
    def __init__(self):
        self.hist = collections.deque(maxlen=30)
        self.hwnd = None
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)
        self.label = tk.Label(self.root, text="DeepSeek ...", fg=FG, bg=BG, font=("Segoe UI", 9))
        self.label.pack(padx=4, pady=1)
        self.root.update_idletasks()
        self.me = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
        self.poll_balance()
        self.follow()
        self.root.mainloop()

    def follow(self):
        """Every 300 ms: stick to the Codex footer, or hide if Codex is not the front window."""
        if not self.hwnd or not user32.IsWindow(self.hwnd):
            self.hwnd = codex_window()
        fg = user32.GetForegroundWindow()
        show = bool(self.hwnd) and not user32.IsIconic(self.hwnd) and (fg in (self.hwnd, self.me) or os.environ.get("WIDGET_ALWAYS") == "1")
        if show:
            r = W.RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(r))
            h = self.root.winfo_reqheight()
            self.root.geometry(f"+{r.left + X_FROM_LEFT}+{r.bottom - Y_FROM_BOTTOM - h // 2}")
            self.root.deiconify()
            self.root.lift()
        else:
            self.root.withdraw()
        self.root.after(300, self.follow)

    def poll_balance(self):
        threading.Thread(target=self.fetch, daemon=True).start()
        self.root.after(REFRESH_S * 1000, self.poll_balance)

    def fetch(self):
        try:
            bal, cur = balance()
        except Exception as e:
            self.root.after(0, lambda: self.label.config(text=f"DeepSeek ? ({type(e).__name__})"))
            return
        now = time.time()
        self.hist.append((now, bal))
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "balance": bal, "currency": cur,
                                "src": "widget"}) + "\n")
        old = [(t, b) for t, b in self.hist if now - t >= 540]
        rate = ""
        if old:
            t0, b0 = old[-1]
            spent = b0 - bal
            per_h = spent / ((now - t0) / 3600)
            rate = f"  |  10 min {spent * 100:.0f} c" + (f", ~{bal / per_h:.1f} h" if per_h > 0 else "")
        text = f"$ {bal:.2f}{rate}"
        color = FG_WARN if bal < WARN_USD else FG
        self.root.after(0, lambda: self.label.config(text=text, fg=color))


if __name__ == "__main__":
    Widget()
