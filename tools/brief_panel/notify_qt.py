"""A notification window that belongs to us.

Chrome's app mode always draws its own title bar, so the window was never ours.
This one is frameless and painted by hand: our background, our mark, our type.
It reads the same brief.json the panel reads, slides in at the bottom right,
counts itself out, and never dismisses an urgent item on its own.

    python tools/brief_panel/notify_qt.py            # show if anything waits
    python tools/brief_panel/notify_qt.py --demo     # show with sample data
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRectF, Qt,
                          QTimer)
from PyQt6.QtGui import (QColor, QFont, QFontMetrics, QPainter, QPainterPath,
                         QPixmap)
from PyQt6.QtWidgets import QApplication, QWidget

ROOT = Path(__file__).resolve().parents[2]
BRIEF = ROOT / "agora_output" / "channels" / "brief.json"
PANEL = Path(__file__).resolve().parent / "show.ps1"
LOGO = ROOT / "public" / "sig" / "agora-96.png"

W, H, MARGIN, RADIUS = 380, 156, 20, 14
SECONDS = 12

BG = QColor("#111419")
EDGE = QColor("#232936")
TEXT = QColor("#e9ecf1")
DIM = QColor("#8b93a1")
URGENT = QColor("#e5533d")
WAITING = QColor("#d9a441")


def read_brief(demo: bool) -> dict | None:
    if demo:
        return {"items": [
            {"state": "URGENT", "title": "release v3.6.2 spadol po publikovaní",
             "who": "GitHub Actions · inspeximus"},
            {"state": "WAITING", "title": "Yasha čaká na defended row", "who": "agmi #3"},
            {"state": "WAITING", "title": "MemStrata mlčí od 21. 9.", "who": "Discussion #2"},
        ]}
    try:
        return json.loads(BRIEF.read_text(encoding="utf-8"))
    except Exception:
        return None


class Toast(QWidget):
    def __init__(self, urgent: list, waiting: list) -> None:
        super().__init__()
        self.urgent, self.waiting = urgent, waiting
        self.top = (urgent or waiting)[0]
        self.accent = URGENT if urgent else WAITING
        self.left_ms = SECONDS * 1000
        self.paused = False
        self.beat = 0.0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool          # keeps it off the taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(W, H)
        self.logo = QPixmap(str(LOGO)) if LOGO.exists() else QPixmap()

        area = QApplication.primaryScreen().availableGeometry()
        self.end_pos = QPoint(area.right() - W - MARGIN, area.bottom() - H - MARGIN)
        self.move(self.end_pos + QPoint(40, 0))
        self.setWindowOpacity(0.0)

        self.slide = QPropertyAnimation(self, b"pos", self)
        self.slide.setDuration(260)
        self.slide.setStartValue(self.pos())
        self.slide.setEndValue(self.end_pos)
        self.slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade = QPropertyAnimation(self, b"windowOpacity", self)
        self.fade.setDuration(220)
        self.fade.setStartValue(0.0)
        self.fade.setEndValue(1.0)

        self.tick = QTimer(self)
        self.tick.timeout.connect(self._tick)
        self.tick.start(60)

    def show_in(self) -> None:
        self.show()
        self.slide.start()
        self.fade.start()

    def _tick(self) -> None:
        self.beat = (self.beat + 0.06) % 6.283
        if not self.urgent and not self.paused:
            self.left_ms -= 60
            if self.left_ms <= 0:
                self.close()
                return
        self.update()

    def enterEvent(self, _e) -> None:
        self.paused = True

    def leaveEvent(self, _e) -> None:
        self.paused = False

    def mousePressEvent(self, e) -> None:
        if e.position().x() > W - 34 and e.position().y() < 34:
            self.close()
            return
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
             "-ExecutionPolicy", "Bypass", "-File", str(PANEL), "-NoToast"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.close()

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_Escape:
            self.close()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        card = QRectF(0, 0, W, H)
        path = QPainterPath()
        path.addRoundedRect(card, RADIUS, RADIUS)
        p.fillPath(path, BG)
        p.setPen(EDGE)
        p.drawPath(path)

        # accent edge, the one piece of colour that carries the meaning
        edge = QPainterPath()
        edge.addRoundedRect(QRectF(0, 0, 4, H), 2, 2)
        p.fillPath(edge, self.accent)

        y = 18
        if not self.logo.isNull():
            p.drawPixmap(20, y, 18, 18, self.logo.scaled(
                36, 36, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        p.setPen(DIM)
        f = QFont("Segoe UI", 8)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
        f.setCapitalization(QFont.Capitalization.AllUppercase)
        p.setFont(f)
        p.drawText(46, y + 14, "Agora brief")

        if self.urgent:  # a slow beat, only where it is earned
            import math
            a = 120 + int(100 * (1 + math.sin(self.beat)) / 2)
            dot = QColor(self.accent)
            dot.setAlpha(a)
            p.setBrush(dot)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(W - 30, y + 4, 8, 8)

        p.setPen(DIM)
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(W - 30, y + 14, "×")

        p.setPen(TEXT)
        head = QFont("Segoe UI Semibold", 13)
        p.setFont(head)
        p.drawText(20, 68, f"{len(self.waiting)} čaká · {len(self.urgent)} urgentné")

        p.setPen(DIM)
        body = QFont("Segoe UI", 9)
        p.setFont(body)
        title = QFontMetrics(body).elidedText(
            self.top.get("title", ""), Qt.TextElideMode.ElideRight, W - 40)
        p.drawText(20, 90, title)
        who = QFontMetrics(body).elidedText(
            self.top.get("who", ""), Qt.TextElideMode.ElideRight, W - 40)
        p.setPen(QColor("#6b7280"))
        p.drawText(20, 108, who)

        p.setPen(DIM)
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(20, H - 18, "Klikni a otvor panel" if self.urgent
                   else "Klikni a otvor panel · zmizne samo")

        if not self.urgent:  # the countdown, hairline thin
            frac = max(0.0, self.left_ms / (SECONDS * 1000))
            p.fillRect(QRectF(0, H - 3, W * frac, 3), EDGE)


def main() -> int:
    demo = "--demo" in sys.argv
    data = read_brief(demo)
    items = (data or {}).get("items") or []
    urgent = [i for i in items if i.get("state") == "URGENT"]
    waiting = [i for i in items if i.get("state") == "WAITING"]
    if not urgent and not waiting:
        return 0
    hour = __import__("datetime").datetime.now().hour
    if not demo and (hour >= 22 or hour < 7):  # quiet hours
        return 0

    app = QApplication(sys.argv)
    toast = Toast(urgent, waiting)
    toast.show_in()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
