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
BG = "#1d1d1d"            # made fully transparent below; close to the footer so glyph edges blend
FG, FG_WARN = "#f2c14e", "#ff6b6b"
FONT_FILE = os.path.join(os.path.expanduser("~"), ".codex", "fonts", "HarryP.ttf")   # "Harry P" by Graham Meade, as in the ftmo-lab monitor
FONT = ("Harry P", -30)    # negative = pixels
# Physical pixels, relative to the Codex window: the free part of the sidebar footer row sits
# between the "deepseek" profile name (ends ~160) and the update icon (starts ~500).
FREE_LEFT, FREE_RIGHT = 165, 495
ROW_FROM_BOTTOM = 31       # centre line of the settings row
CODEX_TITLE = "ChatGPT"    # the Codex desktop app's window title

ctypes.windll.shcore.SetProcessDpiAwareness(2)   # per-monitor aware: crisp text, physical coordinates
ctypes.windll.gdi32.AddFontResourceExW(FONT_FILE, 0x10, 0)   # FR_PRIVATE: this process only
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


def frame_rect(hwnd):
    """The visible window rectangle (DWM frame bounds), clipped to its monitor's work area so a
    maximized window never places the label under the taskbar."""
    r = W.RECT()
    if ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:
        user32.GetWindowRect(hwnd, ctypes.byref(r))

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", W.DWORD), ("rcMonitor", W.RECT), ("rcWork", W.RECT), ("dwFlags", W.DWORD)]

    mi = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    if user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(mi)):
        r.left, r.top = max(r.left, mi.rcWork.left), max(r.top, mi.rcWork.top)
        r.right, r.bottom = min(r.right, mi.rcWork.right), min(r.bottom, mi.rcWork.bottom)
    return r


class Widget:
    def __init__(self):
        self.hist = collections.deque(maxlen=120)
        self.load_history()
        self.hwnd = None
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)
        self.root.wm_attributes("-transparentcolor", BG)   # no box: only the glyphs are drawn
        self.label = tk.Label(self.root, text="DeepSeek ...", fg=FG, bg=BG, font=FONT)
        self.label.pack(padx=6, pady=0)
        self.root.update_idletasks()
        self.me = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
        self.poll_balance()
        self.follow()
        self.root.mainloop()

    def load_history(self):
        """Readings from the last hour (this widget and the notify hook), so the rate shows at once."""
        cutoff = time.time() - 3600
        try:
            for line in LOG.read_text(encoding="utf-8").splitlines():
                d = json.loads(line)
                t = time.mktime(time.strptime(d["t"], "%Y-%m-%dT%H:%M:%S"))
                if t >= cutoff:
                    self.hist.append((t, float(d["balance"])))
        except Exception:
            pass

    def follow(self):
        """Every 300 ms: stick to the Codex footer, or hide if Codex is not the front window."""
        if not self.hwnd or not user32.IsWindow(self.hwnd):
            self.hwnd = codex_window()
        fg = user32.GetForegroundWindow()
        show = bool(self.hwnd) and not user32.IsIconic(self.hwnd) and (fg in (self.hwnd, self.me) or os.environ.get("WIDGET_ALWAYS") == "1")
        if show:
            r = frame_rect(self.hwnd)
            w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
            x = r.left + (FREE_LEFT + FREE_RIGHT) // 2 - w // 2
            self.root.geometry(f"+{x}+{r.bottom - ROW_FROM_BOTTOM - h // 2}")
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
            rate = f"   {spent * 100:.0f}c/10min" + (f"  {bal / per_h:.0f}h" if per_h > 0 else "")
        text = f"$ {bal:.2f}{rate}"
        color = FG_WARN if bal < WARN_USD else FG
        self.root.after(0, lambda: self.label.config(text=text, fg=color))


if __name__ == "__main__":
    Widget()
