"""Generate the Aurora Clock application icon (multi-resolution .ico)."""
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
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import struct
import zlib

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QApplication

app = QApplication([])
SIZES = [256, 128, 64, 48, 32, 24, 16]
BG1, BG2 = "#122A3C", "#07131E"
ACCENT, FG = "#38E1C6", "#EAF6FF"

def render(sz: int) -> QImage:
    img = QImage(sz, sz, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    m = sz * 0.03
    r = QRectF(m, m, sz - 2*m, sz - 2*m)
    cx = cy = sz / 2.0
    rad = r.width() / 2.0

    g = QRadialGradient(QPointF(cx, cy * 0.75), rad * 1.25)
    g.setColorAt(0.0, QColor(BG1)); g.setColorAt(1.0, QColor(BG2))
    p.setPen(Qt.NoPen); p.setBrush(QBrush(g)); p.drawEllipse(r)

    ring = QColor(ACCENT); ring.setAlphaF(0.95)
    p.setPen(QPen(ring, max(1.0, sz * 0.045))); p.setBrush(Qt.NoBrush)
    p.drawEllipse(r.adjusted(sz*0.035, sz*0.035, -sz*0.035, -sz*0.035))

    if sz >= 32:
        p.setPen(QPen(QColor(FG), max(1.0, sz * 0.022), Qt.SolidLine, Qt.RoundCap))
        for i in range(12):
            import math
            a = math.radians(i * 30)
            r1 = rad * 0.70 if i % 3 == 0 else rad * 0.745
            r2 = rad * 0.80
            p.drawLine(QPointF(cx + math.sin(a)*r1, cy - math.cos(a)*r1),
                       QPointF(cx + math.sin(a)*r2, cy - math.cos(a)*r2))

    p.save(); p.translate(cx, cy)
    # 10:10 - the classic clock-logo pose, plus a teal second hand
    p.setPen(QPen(QColor(FG), max(1.4, sz*0.065), Qt.SolidLine, Qt.RoundCap))
    p.save(); p.rotate(-60); p.drawLine(QPointF(0, rad*0.10), QPointF(0, -rad*0.36)); p.restore()
    p.setPen(QPen(QColor(FG), max(1.2, sz*0.048), Qt.SolidLine, Qt.RoundCap))
    p.save(); p.rotate(60);  p.drawLine(QPointF(0, rad*0.12), QPointF(0, -rad*0.54)); p.restore()
    if sz >= 48:
        p.setPen(QPen(QColor(ACCENT), max(1.0, sz*0.022), Qt.SolidLine, Qt.RoundCap))
        p.save(); p.rotate(150); p.drawLine(QPointF(0, rad*0.16), QPointF(0, -rad*0.60)); p.restore()
    p.setPen(Qt.NoPen); p.setBrush(QBrush(QColor(FG)))
    p.drawEllipse(QPointF(0, 0), sz*0.035, sz*0.035)
    p.setBrush(QBrush(QColor(ACCENT)))
    p.drawEllipse(QPointF(0, 0), sz*0.016, sz*0.016)
    p.restore(); p.end()
    return img

def png_bytes(img: QImage) -> bytes:
    """Encode QImage as PNG by hand (keeps the ICO container exact)."""
    w, h = img.width(), img.height()
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            c = img.pixelColor(x, y)
            raw += bytes((c.red(), c.green(), c.blue(), c.alpha()))
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))

out = sys.argv[1] if len(sys.argv) > 1 else "aurora.ico"
images = [(s, png_bytes(render(s))) for s in SIZES]
hdr = struct.pack("<HHH", 0, 1, len(images))
offset = 6 + 16 * len(images)
entries, blobs = b"", b""
for s, data in images:
    entries += struct.pack("<BBBBHHII", 0 if s >= 256 else s, 0 if s >= 256 else s,
                           0, 0, 1, 32, len(data), offset)
    blobs += data
    offset += len(data)
with open(out, "wb") as fh:
    fh.write(hdr + entries + blobs)
print("wrote", out, os.path.getsize(out), "bytes")
# also a PNG for the installer / docs
render(256).save(os.path.splitext(out)[0] + ".png")
