"""A notification window that belongs to us.

Chrome's app mode always draws its own title bar, so the window was never ours.
This one is frameless and painted by hand: our background, our mark, our type.
It reads the same brief.json the panel reads, slides in at the bottom right,
counts itself out, and never dismisses an urgent item on its own.

    python tools/brief_panel/notify_qt.py            # show if anything waits
    python tools/brief_panel/notify_qt.py --demo     # show with sample data
    pythonw tools/brief_panel/notify_qt.py --tray    # live in the tray, watch the file
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRectF, Qt,
                          QTimer)
from PyQt6.QtGui import (QAction, QColor, QFont, QFontMetrics, QIcon, QImage,
                         QPainter, QPainterPath, QPixmap)
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

ROOT = Path(__file__).resolve().parents[2]
BRIEF = ROOT / "agora_output" / "channels" / "brief.json"
PANEL = Path(__file__).resolve().parent / "show.ps1"
LOGO = ROOT / "public" / "sig" / "agora-96.png"

W, H, MARGIN, RADIUS = 340, 104, 18, 12
BADGE, BADGE_R = 40, 10
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
        self.hover_close = False
        self.setMouseTracking(True)

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

    def mouseMoveEvent(self, e) -> None:
        near = e.position().x() > W - 34 and e.position().y() < 32
        if near != self.hover_close:
            self.hover_close = near
            self.update()

    def enterEvent(self, _e) -> None:
        self.paused = True

    def leaveEvent(self, _e) -> None:
        self.paused = False

    def mousePressEvent(self, e) -> None:
        if e.position().x() > W - 34 and e.position().y() < 32:
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

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, W, H), RADIUS, RADIUS)
        p.fillPath(path, BG)
        p.setPen(EDGE)
        p.drawPath(path)

        # The left edge carries the urgency. One signal, one place, so the corner
        # does not need a second one competing with the close button.
        edge = QPainterPath()
        edge.addRoundedRect(QRectF(0, 0, 3, H), 1.5, 1.5)
        p.fillPath(edge, self.accent)

        # The mark is shown whole, in its own rounded tile, the way an app icon sits
        # in a notification. Clipping to the same curvature as the card keeps the
        # black field from reading as a hard-cornered box.
        if not self.logo.isNull():
            tile = QRectF(16, (H - BADGE) / 2, BADGE, BADGE)
            clip = QPainterPath()
            clip.addRoundedRect(tile, BADGE_R, BADGE_R)
            p.save()
            p.setClipPath(clip)
            p.drawPixmap(tile.toRect(), self.logo.scaled(
                BADGE * 3, BADGE * 3, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation))
            p.restore()
            p.setPen(QColor("#2b3240"))
            p.drawPath(clip)

        x = 16 + BADGE + 14
        p.setPen(DIM)
        eyebrow = QFont("Segoe UI", 7)
        eyebrow.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
        eyebrow.setCapitalization(QFont.Capitalization.AllUppercase)
        p.setFont(eyebrow)
        p.drawText(x, 34, "Agora brief")

        p.setPen(QColor("#5b6472") if not self.hover_close else TEXT)
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(QRectF(W - 30, 12, 18, 18),
                   Qt.AlignmentFlag.AlignCenter, "×")

        p.setPen(TEXT)
        p.setFont(QFont("Segoe UI Semibold", 11))
        p.drawText(x, 58, f"{len(self.waiting)} čaká · {len(self.urgent)} urgentné")

        p.setPen(DIM)
        body = QFont("Segoe UI", 8)
        p.setFont(body)
        p.drawText(x, 78, QFontMetrics(body).elidedText(
            self.top.get("title", ""), Qt.TextElideMode.ElideRight, W - x - 16))

        # One faint hint, right aligned, so the card says what a click does without
        # spending a row on it.
        p.setPen(QColor("#5b6472"))
        hint = QFont("Segoe UI", 7)
        p.setFont(hint)
        p.drawText(QRectF(0, 76, W - 16, 14),
                   Qt.AlignmentFlag.AlignRight, "otvoriť →")

        if not self.urgent:
            frac = max(0.0, self.left_ms / (SECONDS * 1000))
            p.fillRect(QRectF(0, H - 2, W * frac, 2), EDGE)


def counts(data: dict | None) -> tuple[list, list]:
    items = (data or {}).get("items") or []
    return ([i for i in items if i.get("state") == "URGENT"],
            [i for i in items if i.get("state") == "WAITING"])


def quiet_now() -> bool:
    h = __import__("datetime").datetime.now().hour
    return h >= 22 or h < 7


def open_panel() -> None:
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
         "-ExecutionPolicy", "Bypass", "-File", str(PANEL), "-NoToast"],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


class Tray:
    """Lives in the tray so the panel is one click away at any hour.

    It watches brief.json and raises the window only when the set of open items
    CHANGES. A toast on every poll would be the same alarm six times a day for
    work already seen, which is how an alert becomes wallpaper.
    """

    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.seen: set[str] = set()
        self.toast: Toast | None = None
        # The tray scales the icon down hard, so give it the mark on its own field
        # rather than a 192 px badge squeezed into 16 px of tray.
        self.icon = QSystemTrayIcon(QIcon(str(LOGO)) if LOGO.exists() else QIcon())
        self.icon.setToolTip("Agora brief")
        menu = QMenu()
        self.status = QAction("Agora brief", menu)
        self.status.setEnabled(False)
        menu.addAction(self.status)
        menu.addSeparator()
        act_open = QAction("Otvoriť panel", menu)
        act_open.triggered.connect(open_panel)
        menu.addAction(act_open)
        act_show = QAction("Ukázať oznámenie", menu)
        act_show.triggered.connect(lambda: self.raise_toast(force=True))
        menu.addAction(act_show)
        menu.addSeparator()
        act_quit = QAction("Ukončiť", menu)
        act_quit.triggered.connect(app.quit)
        menu.addAction(act_quit)
        self.icon.setContextMenu(menu)
        self.icon.activated.connect(
            lambda r: open_panel() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.icon.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self.poll)
        self.timer.start(60_000)
        self.poll()

    def poll(self) -> None:
        data = read_brief(False)
        urgent, waiting = counts(data)
        self.icon.setToolTip(f"Agora: {len(waiting)} čaká, {len(urgent)} urgentné")
        self.status.setText(f"{len(waiting)} čaká · {len(urgent)} urgentné")
        ids = {i.get("id") for i in urgent + waiting}
        if ids - self.seen and not quiet_now():
            self.raise_toast()
        self.seen = ids

    def raise_toast(self, force: bool = False) -> None:
        data = read_brief(False)
        urgent, waiting = counts(data)
        if not urgent and not waiting:
            if force:
                self.icon.showMessage("Agora brief", "Nič nečaká.",
                                      QSystemTrayIcon.MessageIcon.NoIcon, 3000)
            return
        if self.toast is not None:
            self.toast.close()
        self.toast = Toast(urgent, waiting)
        self.toast.show_in()


def main() -> int:
    if "--tray" in sys.argv:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # the tray outlives every toast
        Tray(app)
        return app.exec()

    demo = "--demo" in sys.argv
    data = read_brief(demo)
    urgent, waiting = counts(data)
    if not urgent and not waiting:
        return 0
    if not demo and quiet_now():
        return 0

    app = QApplication(sys.argv)
    toast = Toast(urgent, waiting)
    toast.show_in()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
