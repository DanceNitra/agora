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
import re
import tkinter as tk
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from deepseek_balance_notify import LOG, balance

REFRESH_S = 30             # balance API; it returns whole cents, measured 40 calls at 4/s: all 200, median 292 ms
METER_S = 2                # token meter: Codex writes a token_count event after every model call
SESSIONS = Path.home() / ".codex" / "sessions"
# deepseek-flash USD per 1M tokens (api-docs.deepseek.com/quick_start/pricing, read 2026-09-26):
# (cache hit, cache miss, output). Peak is 01-04 and 06-10 UTC Mon-Fri; every other hour is half price.
PRICE_PEAK, PRICE_OFF = (0.006, 0.3, 1.2), (0.003, 0.15, 0.6)
WARN_USD = 0.50
BG = "#1d1d1d"            # made fully transparent below; close to the footer so glyph edges blend
FG, FG_WARN = "#f2c14e", "#ff6b6b"
FONT_FILE = os.path.join(os.path.expanduser("~"), ".codex", "fonts", "HarryP.ttf")   # "Harry P" by Graham Meade, as in the ftmo-lab monitor
FONT = ("Harry P", -30)    # negative = pixels
# Physical pixels, relative to the Codex window: the free part of the sidebar footer row sits
# between the "deepseek" profile name (ends ~160) and the update icon (starts ~500).
FREE_LEFT, FREE_RIGHT = 165, 495
ROW_FROM_BOTTOM = 31       # centre line of the settings row
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"
AGORA_ENV = Path(__file__).resolve().parent.parent / "server" / ".env"   # holds the Ollama key as AGORA_API_KEY
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


def codex_on_deepseek():
    """True while Codex talks to the DeepSeek API (tools/codex_provider.py use deepseek)."""
    try:
        m = re.search(r'^model_provider\s*=\s*"([^"]+)"', CODEX_CONFIG.read_text(encoding="utf-8"), re.M)
        return bool(m) and m.group(1) == "agora_deepseek"
    except OSError:
        return True


def ollama_usage():
    """Ollama plan limits as fractions 0..1: (session = the 5-hour window, weekly).
    GET https://ollama.com/api/usage with the account API key; undocumented, found 2026-09-26."""
    key = re.search(r'^AGORA_API_KEY\s*=\s*"?([^"\n]+)', AGORA_ENV.read_text(encoding="utf-8"), re.M).group(1).strip()
    req = urllib.request.Request("https://ollama.com/api/usage", headers={"Authorization": f"Bearer {key}"})
    lim = json.load(urllib.request.urlopen(req, timeout=15))["limits"]
    return float(lim["session"]["usage"]), float(lim["weekly"]["usage"])


def price_at(ts):
    t = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.now(timezone.utc)
    peak = t.weekday() < 5 and (1 <= t.hour < 4 or 6 <= t.hour < 10)
    return PRICE_PEAK if peak else PRICE_OFF


class TokenMeter:
    """Live spend from the Codex thread files: every token_count event carries the thread's running
    totals, so the cost of each model call is the difference between two totals times the price."""

    def __init__(self):
        self.pos, self.total = {}, {}
        self.events = collections.deque()          # (epoch seconds, usd)

    def scan(self):
        now = time.time()
        try:
            files = [f for f in SESSIONS.rglob("rollout-*.jsonl") if now - f.stat().st_mtime < 7200]
        except OSError:
            return
        for f in files:
            size = f.stat().st_size
            start = self.pos.get(f)
            if start is None:
                start = max(0, size - 4_000_000)   # a thread can be 200 MB; the last 4 MB covers the last hour
            if size <= start:
                self.pos[f] = size
                continue
            with f.open("rb") as fh:
                fh.seek(start)
                chunk = fh.read()
            cut = chunk.rfind(bytes([10])) + 1
            self.pos[f] = start + cut
            for line in chunk[:cut].splitlines():
                if b'"token_count"' not in line:
                    continue
                try:
                    d = json.loads(line)
                    u = d["payload"]["info"]["total_token_usage"]
                except Exception:
                    continue
                tot = (u.get("input_tokens", 0), u.get("cached_input_tokens", 0), u.get("output_tokens", 0))
                prev = self.total.get(f)
                self.total[f] = tot
                if prev is None or tot == prev:
                    continue
                inp, hit, out = (max(0, a - b) for a, b in zip(tot, prev))
                p_hit, p_miss, p_out = price_at(d.get("timestamp"))
                usd = (hit * p_hit + max(0, inp - hit) * p_miss + out * p_out) / 1e6
                ts = d.get("timestamp")
                t = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() if ts else now
                self.events.append((t, usd))
        while self.events and now - self.events[0][0] > 3600:
            self.events.popleft()

    def spent(self, seconds):
        now = time.time()
        return sum(u for t, u in self.events if now - t <= seconds)


class Widget:
    def __init__(self):
        self.hist = collections.deque(maxlen=240)
        self.load_history()
        self.meter = TokenMeter()
        self.bal = self.cur = None
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
        self.tick_meter()
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
        if not codex_on_deepseek():
            return self.fetch_ollama()
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
        self.bal, self.cur = bal, cur
        self.root.after(0, self.render)

    def tick_meter(self):
        if codex_on_deepseek():
            threading.Thread(target=lambda: (self.meter.scan(), self.root.after(0, self.render)), daemon=True).start()
        self.root.after(METER_S * 1000, self.tick_meter)

    def render(self):
        """$ balance (API, whole cents), cents per minute over the last 5 minutes of model calls,
        and hours left at the last hour's pace. Both rates come from token counts, so they move
        within seconds of a call instead of waiting for the balance to drop a whole cent."""
        if self.bal is None or not codex_on_deepseek():
            return
        per_min = self.meter.spent(300) / 5
        hour = self.meter.spent(3600)
        span = min(3600, time.time() - self.meter.events[0][0]) if self.meter.events else 0
        per_h = hour / (span / 3600) if span >= 300 else per_min * 60
        left = f"  {self.bal / per_h:.0f}h" if per_h > 0 else "  --h"
        text = f"$ {self.bal:.2f}   {per_min * 100:.1f}c/min{left}"
        self.label.config(text=text, fg=FG_WARN if self.bal < WARN_USD else FG)


    def fetch_ollama(self):
        try:
            session, weekly = ollama_usage()
        except Exception as e:
            self.root.after(0, lambda: self.label.config(text=f"Ollama ? ({type(e).__name__})", fg=FG))
            return
        text = f"5h {session * 100:.0f}%   week {weekly * 100:.0f}%"
        color = FG_WARN if max(session, weekly) >= 0.9 else FG
        self.root.after(0, lambda: self.label.config(text=text, fg=color))


if __name__ == "__main__":
    Widget()
