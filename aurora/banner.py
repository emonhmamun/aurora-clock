"""Aurora Clock - on-screen notification banner (toast)."""
# Aurora Clock - a lightweight desktop clock overlay for Windows.
# Copyright (C) 2026 Emon Hasan Mamun
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import QBrush, QColor, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class Banner(QWidget):
    """A small frameless toast that slides in at the top-right of the screen."""

    def __init__(self, title: str, body: str, color: str = "#38E1C6",
                 seconds: int = 7, parent=None):
        super().__init__(parent)
        self.title, self.body, self.color = title, body, color
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool |
                            Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(380, 92)

        sc = QGuiApplication.primaryScreen().availableGeometry()
        self._end = QPoint(sc.right() - self.width() - 24, sc.top() + 24)
        self._start = QPoint(sc.right() + 10, sc.top() + 24)
        self.move(self._start)

        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(380)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setStartValue(self._start)
        self._anim.setEndValue(self._end)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(max(2, seconds) * 1000)
        self._hide_timer.timeout.connect(self._dismiss)

    def pop(self) -> None:
        self.show()
        self._anim.start()
        self._hide_timer.start()

    def _dismiss(self) -> None:
        out = QPropertyAnimation(self, b"windowOpacity", self)
        out.setDuration(320)
        out.setStartValue(1.0)
        out.setEndValue(0.0)
        out.finished.connect(self.close)
        out.finished.connect(self.deleteLater)
        self._fade = out
        out.start()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(r, 14, 14)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(13, 23, 36, 242)))
        p.drawPath(path)
        edge = QColor(self.color); edge.setAlphaF(0.65)
        p.setPen(QPen(edge, 1.4)); p.setBrush(Qt.NoBrush); p.drawPath(path)

        # accent stripe
        p.save(); p.setClipPath(path)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(QColor(self.color)))
        p.drawRect(QRectF(r.left(), r.top(), 5, r.height()))
        p.restore()

        f = p.font(); f.setPixelSize(16); f.setBold(True)
        p.setFont(f); p.setPen(QPen(QColor("#EAF6FF")))
        p.drawText(QRectF(r.left() + 18, r.top() + 12, r.width() - 30, 22),
                   Qt.AlignLeft | Qt.AlignVCenter, self.title)
        f.setPixelSize(12); f.setBold(False)
        p.setFont(f); p.setPen(QPen(QColor("#9FB4C6")))
        p.drawText(QRectF(r.left() + 18, r.top() + 36, r.width() - 32, 46),
                   Qt.AlignLeft | Qt.TextWordWrap, self.body)
        p.end()
