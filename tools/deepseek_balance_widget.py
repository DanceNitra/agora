# -*- coding: utf-8 -*-
"""deepseek_balance_widget.py - a small always-on-top window with the live DeepSeek balance.

Refreshes every 60 s, shows the balance and the spend over the last 10 minutes, and turns red
under 0.50 USD. Codex's notify toast only fires when a turn ENDS, and a goal turn can run for
hours, so this is the view that updates while Codex works. Drag it with the mouse; close with x.

    pythonw tools\\deepseek_balance_widget.py
"""
import collections
import json
import threading
import time
import tkinter as tk
import urllib.request

from deepseek_balance_notify import LOG, balance

REFRESH_S = 60
WARN_USD = 0.50


class Widget:
    def __init__(self):
        self.hist = collections.deque(maxlen=30)
        self.root = tk.Tk()
        self.root.title("DeepSeek")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.geometry(f"+{self.root.winfo_screenwidth() - 250}+40")
        self.frame = tk.Frame(self.root, bg="#1e1e1e", padx=10, pady=6)
        self.frame.pack()
        self.big = tk.Label(self.frame, text="DeepSeek ...", fg="#e6e6e6", bg="#1e1e1e", font=("Segoe UI", 13, "bold"))
        self.big.pack(anchor="w")
        self.small = tk.Label(self.frame, text="", fg="#9a9a9a", bg="#1e1e1e", font=("Segoe UI", 9))
        self.small.pack(anchor="w")
        close = tk.Label(self.frame, text="x", fg="#777", bg="#1e1e1e", cursor="hand2")
        close.place(relx=1.0, x=4, y=-4, anchor="ne")
        close.bind("<Button-1>", lambda _: self.root.destroy())
        for w in (self.frame, self.big, self.small):
            w.bind("<ButtonPress-1>", self.start_drag)
            w.bind("<B1-Motion>", self.drag)
        self.poll()
        self.root.mainloop()

    def start_drag(self, e):
        self._dx, self._dy = e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y()

    def drag(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def poll(self):
        threading.Thread(target=self.fetch, daemon=True).start()
        self.root.after(REFRESH_S * 1000, self.poll)

    def fetch(self):
        try:
            bal, cur = balance()
        except Exception as e:
            self.root.after(0, lambda: self.small.config(text=f"chyba: {type(e).__name__}"))
            return
        now = time.time()
        self.hist.append((now, bal))
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "balance": bal, "currency": cur, "src": "widget"}) + "\n")
        old = [b for t, b in self.hist if now - t >= 540]
        rate = ""
        if old:
            spent10 = old[-1] - bal
            per_min = spent10 / ((now - [t for t, b in self.hist if b == old[-1]][-1]) / 60)
            left = f", vydrzi ~{bal / per_min / 60:.1f} h" if per_min > 0 else ""
            rate = f"za 10 min {spent10 * 100:.0f} centov{left}"
        color = "#ff6b6b" if bal < WARN_USD else "#e6e6e6"
        self.root.after(0, lambda: (self.big.config(text=f"DeepSeek {bal:.2f} {cur}", fg=color),
                                    self.small.config(text=(rate or "meriam spotrebu...") + time.strftime("  %H:%M"))))


if __name__ == "__main__":
    Widget()
