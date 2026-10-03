"""Aurora Clock - automatic contrast against the desktop wallpaper.

The clock is transparent, so its readability depends entirely on what is
behind it.  This module looks at the user's wallpaper, measures how bright
the area under each clock is, and lets the renderer flip to light text with a
dark outline (on a bright wallpaper) or dark text with a light outline (on a
dark wallpaper).

It reads the wallpaper *file* rather than grabbing the screen, so there is no
flicker, no screenshot permission and almost no CPU cost.
"""
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

import os
import sys
import time
from typing import Dict, Optional, Tuple

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage

_CACHE: Dict[str, object] = {"path": None, "mtime": 0.0, "image": None, "checked": 0.0}
_REGION: Dict[Tuple[int, int, int, int], Tuple[float, float]] = {}


# ---------------------------------------------------------------- wallpaper
def wallpaper_path() -> Optional[str]:
    if sys.platform != "win32":
        return os.environ.get("AURORA_WALLPAPER")        # handy for testing
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(512)
        # SPI_GETDESKWALLPAPER = 0x0073
        ok = ctypes.windll.user32.SystemParametersInfoW(0x0073, 512, buf, 0)
        if ok and buf.value and os.path.isfile(buf.value):
            return buf.value
    except Exception:
        pass
    return None


def _wallpaper_image() -> Optional[QImage]:
    now = time.time()
    if now - float(_CACHE.get("checked", 0.0)) < 20.0:
        return _CACHE.get("image")          # type: ignore[return-value]
    _CACHE["checked"] = now

    path = wallpaper_path()
    if not path:
        _CACHE["image"] = None
        return None
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return _CACHE.get("image")          # type: ignore[return-value]

    if path == _CACHE.get("path") and mtime == _CACHE.get("mtime"):
        return _CACHE.get("image")          # type: ignore[return-value]

    img = QImage(path)
    if img.isNull():
        _CACHE.update({"path": path, "mtime": mtime, "image": None})
        return None
    # a small copy is all we need for an average
    img = img.scaled(480, 270, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    _CACHE.update({"path": path, "mtime": mtime, "image": img})
    _REGION.clear()
    return img


# ------------------------------------------------------------------ measure
def luminance_under(geo: QRect) -> Optional[float]:
    """Average perceived brightness (0 = black, 1 = white) behind `geo`."""
    img = _wallpaper_image()
    if img is None:
        return None

    screen = QGuiApplication.primaryScreen()
    for sc in QGuiApplication.screens():
        if sc.geometry().intersects(geo):
            screen = sc
            break
    sg = screen.geometry()
    if sg.width() <= 0 or sg.height() <= 0:
        return None

    key = (geo.x(), geo.y(), geo.width(), geo.height())
    cached = _REGION.get(key)
    if cached and time.time() - cached[1] < 20.0:
        return cached[0]

    # map the clock rectangle onto the (stretched) wallpaper
    fx = (geo.x() - sg.x()) / sg.width()
    fy = (geo.y() - sg.y()) / sg.height()
    fw = geo.width() / sg.width()
    fh = geo.height() / sg.height()
    x0 = max(0, min(img.width() - 1, int(fx * img.width())))
    y0 = max(0, min(img.height() - 1, int(fy * img.height())))
    x1 = max(x0 + 1, min(img.width(), int((fx + fw) * img.width())))
    y1 = max(y0 + 1, min(img.height(), int((fy + fh) * img.height())))

    total, count = 0.0, 0
    step_x = max(1, (x1 - x0) // 24)
    step_y = max(1, (y1 - y0) // 24)
    for y in range(y0, y1, step_y):
        for x in range(x0, x1, step_x):
            c = img.pixelColor(x, y)
            # Rec. 709 luma
            total += (0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF())
            count += 1
    if not count:
        return None
    lum = total / count
    _REGION[key] = (lum, time.time())
    return lum


# ------------------------------------------------------------------- apply
def adjust(settings: dict, pal: Dict[str, str], geo: QRect) -> Dict[str, str]:
    """Return a palette tuned for the wallpaper under this clock.

    Also sets the outline colour so the glyphs keep a crisp edge whatever is
    behind them.  Returns the palette unchanged when auto contrast is off or
    the wallpaper cannot be read (a solid-colour desktop, for instance).
    """
    if not settings.get("fx_auto_contrast", False):
        return pal
    lum = luminance_under(geo)
    if lum is None:
        return pal

    strength = max(0.0, min(1.0, float(settings.get("fx_auto_strength", 1.0))))
    out = dict(pal)
    if lum > 0.55:                      # bright wallpaper -> dark text
        target_fg, target_dim, outline = "#101417", "#2E3842", "#FFFFFF"
    else:                               # dark wallpaper -> light text
        target_fg, target_dim, outline = "#FFFFFF", "#C7D3DD", "#000000"

    out["fg"] = _mix(pal.get("fg", "#FFFFFF"), target_fg, strength)
    out["dim"] = _mix(pal.get("dim", "#AAAAAA"), target_dim, strength * 0.85)
    out["_auto_outline"] = outline
    return out


def _mix(a: str, b: str, t: float) -> str:
    ca, cb = QColor(a), QColor(b)
    if not ca.isValid() or not cb.isValid():
        return a
    return QColor(
        round(ca.red() + (cb.red() - ca.red()) * t),
        round(ca.green() + (cb.green() - ca.green()) * t),
        round(ca.blue() + (cb.blue() - ca.blue()) * t),
    ).name()
