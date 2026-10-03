"""Aurora Clock - clock face renderers.

Every face is a function:  render(painter, rect, ctx) -> None
`ctx` carries the resolved time, palette and per-clock settings.
All drawing is resolution independent: the face is laid out inside `rect`.
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

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)


@dataclass
class FaceContext:  # noqa: D101
    now: datetime               # already in the target timezone
    sub_second: float           # 0.0 .. 1.0 fraction of the current second
    pal: Dict[str, str]
    settings: dict
    label: str
    now_utc: datetime | None = None   # corrected UTC, needed by session faces
    sessions: list | None = None      # pre-computed SessionStatus list
    quality: str = "balanced"         # low | balanced | smooth

    # convenience -----------------------------------------------------
    @property
    def hour24(self) -> bool:
        return bool(self.settings.get("hour24", False))

    @property
    def show_seconds(self) -> bool:
        return self.settings.get("seconds_mode", "smooth") != "hidden" and \
            bool(self.settings.get("show_seconds", True))

    @property
    def smooth(self) -> bool:
        return self.settings.get("seconds_mode", "smooth") == "smooth"

    def color(self, key: str, alpha: float = 1.0) -> QColor:
        c = QColor(self.pal.get(key, "#FFFFFF"))
        if alpha < 1.0:
            c.setAlphaF(max(0.0, min(1.0, alpha)))
        return c

    def font(self, size: float, weight: int | None = None, mono: bool = False) -> QFont:
        fam = "Consolas" if mono else self.settings.get("font_family", "Segoe UI")
        f = QFont(fam)
        f.setPixelSize(max(6, int(size)))
        w = weight if weight is not None else int(self.settings.get("font_weight", 300))
        f.setWeight(QFont.Weight(max(1, min(900, w))))
        return f


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Legibility effects engine
# ---------------------------------------------------------------------------
# Drawing goes through a single pipeline so every clock face automatically
# gets shadow / outline / glow / contrast plate without any extra code.

_FX: Dict[str, object] = {}


def set_fx(settings: dict, pal: Dict[str, str], quality: str = "balanced") -> None:
    """Called once per repaint by render()."""
    _FX.clear()
    _FX.update(settings)
    _FX["_pal"] = pal
    _FX["_shadow_steps"] = {"low": 1, "balanced": 3, "smooth": 4}.get(quality, 3)


def _fxf(key: str, default: float) -> float:
    try:
        return float(_FX.get(key, default))
    except (TypeError, ValueError):
        return default


def _fxb(key: str, default: bool) -> bool:
    return bool(_FX.get(key, default))


def _fxc(key: str, default: str) -> str:
    v = _FX.get(key) or default
    return str(v)



# ---------------------------------------------------------------------------
# Gradient fills
# ---------------------------------------------------------------------------
# Ready-made gradients the user can pick in Settings -> Appearance.
GRADIENT_PRESETS: Dict[str, tuple] = {
    "custom":      ("Custom (pick your own)", "#38E1C6", "#6C8CFF"),
    "aurora":      ("Aurora",                 "#38E1C6", "#6C8CFF"),
    "sunset":      ("Sunset",                 "#FF8A3D", "#FF4D7E"),
    "ocean":       ("Ocean",                  "#00E5FF", "#2A6CFF"),
    "lime":        ("Lime Punch",             "#C6FF4D", "#14D672"),
    "gold":        ("Liquid Gold",            "#FFE89B", "#C98A17"),
    "rose":        ("Rose Gold",              "#FFD9C9", "#E2779A"),
    "candy":       ("Cotton Candy",           "#FF9EC4", "#8FC4FF"),
    "fire":        ("Fire",                   "#FFD452", "#FF2D2D"),
    "ice":         ("Ice",                    "#FFFFFF", "#7FC3FF"),
    "violet":      ("Ultraviolet",            "#B15CFF", "#4D2BFF"),
    "emerald":     ("Emerald",                "#9BFFD1", "#0E9F6E"),
    "steel":       ("Brushed Steel",          "#F2F5F8", "#6E7A88"),
    "neon":        ("Neon Split",             "#00FFC2", "#FF00E5"),
    "copper":      ("Copper",                 "#FFC9A0", "#A0522D"),
    "mono":        ("Silver Fade",            "#FFFFFF", "#8A939C"),
    "trader":      ("Trader Green/Red",       "#2BD67B", "#FF5252"),
}

GRADIENT_DIRECTIONS = {
    "vertical":   "Top to bottom",
    "vertical_r": "Bottom to top",
    "horizontal": "Left to right",
    "diagonal":   "Diagonal",
    "radial":     "Centre outwards",
}


def gradient_colors() -> tuple[str, str]:
    name = str(_FX.get("gradient_preset", "custom") or "custom")
    if name != "custom" and name in GRADIENT_PRESETS:
        _l, c1, c2 = GRADIENT_PRESETS[name]
        return c1, c2
    return _fxc("gradient_c1", "#38E1C6"), _fxc("gradient_c2", "#6C8CFF")


def _fill_brush(path: QPainterPath, color: QColor) -> QBrush:
    """Solid colour, or the user's gradient when one is enabled."""
    if not _fxb("gradient_on", False):
        return QBrush(color)
    br = path.boundingRect()
    if br.width() < 1 or br.height() < 1:
        return QBrush(color)
    c1s, c2s = gradient_colors()
    c1, c2 = QColor(c1s), QColor(c2s)
    c1.setAlphaF(color.alphaF()); c2.setAlphaF(color.alphaF())
    d = str(_FX.get("gradient_dir", "vertical") or "vertical")
    if d == "radial":
        g = QRadialGradient(br.center(), max(br.width(), br.height()) * 0.62)
    elif d == "horizontal":
        g = QLinearGradient(br.topLeft(), br.topRight())
    elif d == "diagonal":
        g = QLinearGradient(br.topLeft(), br.bottomRight())
    elif d == "vertical_r":
        g = QLinearGradient(br.bottomLeft(), br.topLeft())
    else:
        g = QLinearGradient(br.topLeft(), br.bottomLeft())
    mid = _fxf("gradient_mid", 0.5)
    g.setColorAt(0.0, c1)
    if 0.05 < mid < 0.95:
        m = QColor((c1.red() + c2.red()) // 2, (c1.green() + c2.green()) // 2,
                   (c1.blue() + c2.blue()) // 2)
        m.setAlphaF(color.alphaF())
        g.setColorAt(mid, m)
    g.setColorAt(1.0, c2)
    return QBrush(g)


def _text_path(rect: QRectF, text: str, font: QFont, align) -> QPainterPath:
    """Lay the string out inside `rect` honouring the alignment flags."""
    fm = QFontMetricsF(font)
    tw = fm.horizontalAdvance(text)
    if align & Qt.AlignHCenter:
        x = rect.left() + (rect.width() - tw) / 2.0
    elif align & Qt.AlignRight:
        x = rect.right() - tw
    else:
        x = rect.left()
    if align & Qt.AlignVCenter:
        y = rect.center().y() + (fm.ascent() - fm.descent()) / 2.0
    elif align & Qt.AlignBottom:
        y = rect.bottom() - fm.descent()
    else:
        y = rect.top() + fm.ascent()
    path = QPainterPath()
    path.addText(QPointF(x, y), font, text)
    return path


def _plate_for(path: QPainterPath) -> QRectF:
    pad = _fxf("fx_plate_pad", 10.0)
    return path.boundingRect().adjusted(-pad, -pad * 0.6, pad, pad * 0.6)


def draw_path_fx(p: QPainter, path: QPainterPath, color: QColor) -> None:
    """Shadow → plate → glow → outline → fill."""
    # 1. contrast plate (drawn first, sits behind everything)
    if _fxb("fx_plate", False):
        plate = QColor(_fxc("fx_plate_color", "#000000"))
        plate.setAlphaF(max(0.0, min(1.0, _fxf("fx_plate_opacity", 0.38))))
        rad = _fxf("fx_plate_radius", 10.0)
        pp = QPainterPath()
        pp.addRoundedRect(_plate_for(path), rad, rad)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(plate))
        p.drawPath(pp)

    # 2. drop shadow — several offset copies approximate a gaussian blur
    if _fxb("fx_shadow", True):
        dx, dy = _fxf("fx_shadow_dx", 2.0), _fxf("fx_shadow_dy", 2.0)
        blur = max(0.0, _fxf("fx_shadow_blur", 7.0))
        base = QColor(_fxc("fx_shadow_color", "#000000"))
        alpha = max(0.0, min(1.0, _fxf("fx_shadow_opacity", 0.80)))
        p.setPen(Qt.NoPen)
        if blur <= 0.5:
            base.setAlphaF(alpha)
            p.setBrush(QBrush(base))
            p.drawPath(path.translated(dx, dy))
        else:
            steps = int(_FX.get("_shadow_steps", 3) or 3)
            for i in range(steps, 0, -1):
                w = blur * i / steps
                c = QColor(base)
                c.setAlphaF(alpha * (0.42 / steps) * (1.0 + (steps - i) * 0.35))
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(c, w * 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawPath(path.translated(dx, dy))
            base.setAlphaF(alpha)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(base))
            p.drawPath(path.translated(dx, dy))

    # 3. glow halo
    glow = _fxf("fx_glow", 0.0)
    if glow > 0.01:
        pal = _FX.get("_pal") or {}
        gc = QColor(_fxc("fx_glow_color", "") or pal.get("glow", "#FFFFFF"))
        p.setBrush(Qt.NoBrush)
        for i, w in enumerate((9.0, 6.0, 3.0)):
            c = QColor(gc)
            c.setAlphaF(min(1.0, glow * (0.10 + i * 0.07)))
            p.setPen(QPen(c, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(path)

    # 4. outline
    ow = _fxf("fx_outline", 0.0)
    if ow > 0.05:
        oc = QColor(_fxc("fx_outline_color", "#000000"))
        oc.setAlphaF(max(0.0, min(1.0, _fxf("fx_outline_opacity", 0.95))))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(oc, ow * 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)

    # 5. the glyphs themselves (solid colour or the user's gradient)
    p.setPen(Qt.NoPen)
    p.setBrush(_fill_brush(path, color))
    p.drawPath(path)


def draw_shape_fx(p: QPainter, path: QPainterPath, pen: QPen) -> None:
    """Same treatment for stroked shapes such as analog hands."""
    stroker_outline = _fxf("fx_outline", 0.0)
    if _fxb("fx_shadow", True):
        dx, dy = _fxf("fx_shadow_dx", 2.0), _fxf("fx_shadow_dy", 2.0)
        c = QColor(_fxc("fx_shadow_color", "#000000"))
        c.setAlphaF(max(0.0, min(1.0, _fxf("fx_shadow_opacity", 0.80))) * 0.85)
        sp = QPen(pen); sp.setColor(c)
        sp.setWidthF(pen.widthF() + max(0.0, _fxf("fx_shadow_blur", 7.0)) * 0.25)
        p.setPen(sp)
        p.drawPath(path.translated(dx, dy))
    if stroker_outline > 0.05:
        oc = QColor(_fxc("fx_outline_color", "#000000"))
        oc.setAlphaF(max(0.0, min(1.0, _fxf("fx_outline_opacity", 0.95))))
        op = QPen(pen); op.setColor(oc); op.setWidthF(pen.widthF() + stroker_outline * 2.0)
        p.setPen(op)
        p.drawPath(path)
    if _fxb("gradient_on", False) and _fxb("gradient_shapes", True):
        gp = QPen(pen)
        gp.setBrush(_fill_brush(path, pen.color()))
        p.setPen(gp)
    else:
        p.setPen(pen)
    p.drawPath(path)


def _fit_text(painter: QPainter, rect: QRectF, text: str, font: QFont,
              color: QColor, align=Qt.AlignCenter, max_ratio: float = 1.0) -> QRectF:
    """Shrink `font` until `text` fits in `rect`, then draw it."""
    f = QFont(font)
    size = f.pixelSize()
    while size > 6:
        f.setPixelSize(size)
        fm = QFontMetricsF(f)
        if fm.horizontalAdvance(text) <= rect.width() * max_ratio and fm.height() <= rect.height():
            break
        size -= 1
    painter.setFont(f)
    if align & Qt.AlignCenter == Qt.AlignCenter:
        a = Qt.AlignHCenter | Qt.AlignVCenter
    else:
        a = align
        if not (a & (Qt.AlignLeft | Qt.AlignRight | Qt.AlignHCenter)):
            a |= Qt.AlignHCenter
        if not (a & (Qt.AlignTop | Qt.AlignBottom | Qt.AlignVCenter)):
            a |= Qt.AlignVCenter
    draw_path_fx(painter, _text_path(rect, text, f, a), color)
    fm = QFontMetricsF(f)
    return QRectF(0, 0, fm.horizontalAdvance(text), fm.height())


def _time_parts(ctx: FaceContext):
    n = ctx.now
    h = n.hour if ctx.hour24 else (n.hour % 12 or 12)
    hh = f"{h:02d}" if (ctx.hour24 or ctx.settings.get("pad_hour", True)) else str(h)
    return hh, f"{n.minute:02d}", f"{n.second:02d}", ("AM" if n.hour < 12 else "PM")


def _date_text(ctx: FaceContext) -> str:
    fmt = ctx.settings.get("date_format", "dddd, d MMMM yyyy")
    n = ctx.now
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    table = {
        "dddd": days[n.weekday()],
        "ddd": days[n.weekday()][:3],
        "dd": f"{n.day:02d}",
        "d": str(n.day),
        "MMMM": months[n.month - 1],
        "MMM": months[n.month - 1][:3],
        "MM": f"{n.month:02d}",
        "M": str(n.month),
        "yyyy": str(n.year),
        "yy": f"{n.year % 100:02d}",
    }
    # single left-to-right pass: longest token wins, output is never re-scanned
    tokens = sorted(table, key=len, reverse=True)
    out, i = [], 0
    while i < len(fmt):
        for t in tokens:
            if fmt.startswith(t, i):
                out.append(table[t])
                i += len(t)
                break
        else:
            out.append(fmt[i])
            i += 1
    return "".join(out)


def _draw_glow_text(painter: QPainter, rect: QRectF, text: str, font: QFont,
                    color: QColor, glow: QColor, strength: float = 1.0, align=Qt.AlignCenter):
    a = align
    if not (a & (Qt.AlignLeft | Qt.AlignRight | Qt.AlignHCenter)):
        a |= Qt.AlignHCenter
    if not (a & (Qt.AlignTop | Qt.AlignBottom | Qt.AlignVCenter)):
        a |= Qt.AlignVCenter
    draw_path_fx(painter, _text_path(rect, text, font, a), color)


# ---------------------------------------------------------------------------
# 1. Digital (classic, big, readable)
# ---------------------------------------------------------------------------

def face_digital(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    hh, mm, ss, ap = _time_parts(ctx)
    show_date = ctx.settings.get("show_date", True)
    show_label = ctx.settings.get("show_label", True) and bool(ctx.label)

    rows = 1 + (1 if show_date else 0) + (1 if show_label else 0)
    time_h = r.height() * (1.0 if rows == 1 else (0.68 if rows == 2 else 0.60))
    y = r.top()

    colon = ":"
    if ctx.settings.get("blink_colon", False) and ctx.sub_second > 0.5:
        colon = " "
    text = f"{hh}{colon}{mm}"
    if ctx.show_seconds:
        text += f"{colon}{ss}"

    time_rect = QRectF(r.left(), y, r.width(), time_h)
    f = ctx.font(time_h * 0.92, int(ctx.settings.get("font_weight", 300)))
    # reserve space for AM/PM
    ampm_on = ctx.settings.get("show_ampm", True) and not ctx.hour24
    main_rect = QRectF(time_rect)
    if ampm_on:
        main_rect.setWidth(time_rect.width() * 0.86)

    _draw_glow_text(p, main_rect, text, _shrink_to_fit(f, text, main_rect),
                    ctx.color("fg"), ctx.color("glow"),
                    1.0 if ctx.settings.get("shadow", True) else 0.0, Qt.AlignCenter)

    if ampm_on:
        af = ctx.font(time_h * 0.26, 600)
        ar = QRectF(main_rect.right() + 4, time_rect.top() + time_h * 0.18,
                    time_rect.width() * 0.14, time_h * 0.5)
        _fit_text(p, ar, ap, af, ctx.color("accent"), Qt.AlignLeft | Qt.AlignVCenter)

    y += time_h
    if show_date:
        dr = QRectF(r.left(), y, r.width(), r.height() * 0.20)
        _fit_text(p, dr, _date_text(ctx), ctx.font(dr.height() * 0.80, 400),
                  ctx.color("dim"), Qt.AlignCenter)
        y += dr.height()
    if show_label:
        lr = QRectF(r.left(), y, r.width(), r.height() * 0.16)
        _fit_text(p, lr, ctx.label.upper(), ctx.font(lr.height() * 0.70, 500),
                  ctx.color("accent", 0.85), Qt.AlignCenter)


def _shrink_to_fit(font: QFont, text: str, rect: QRectF) -> QFont:
    f = QFont(font)
    size = f.pixelSize()
    while size > 6:
        f.setPixelSize(size)
        fm = QFontMetricsF(f)
        if fm.horizontalAdvance(text) <= rect.width() and fm.height() <= rect.height():
            break
        size -= 1
    return f


# ---------------------------------------------------------------------------
# 2. Seven-segment LED
# ---------------------------------------------------------------------------

_SEG_MAP = {
    "0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg",
    "5": "acdfg", "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg",
    " ": "", "-": "g",
}


def _hseg(x: float, y: float, length: float, t: float):
    """Horizontal segment: a flat hexagon centred on the line y."""
    h = t / 2
    return [(x, y), (x + h, y - h), (x + length - h, y - h),
            (x + length, y), (x + length - h, y + h), (x + h, y + h)]


def _vseg(x: float, y: float, length: float, t: float):
    """Vertical segment."""
    h = t / 2
    return [(x, y), (x + h, y + h), (x + h, y + length - h),
            (x, y + length), (x - h, y + length - h), (x - h, y + h)]


def _draw_seg_digit(p: QPainter, r: QRectF, ch: str, on: QColor, off: QColor, thick: float):
    w, h = r.width(), r.height()
    t = thick
    gap = t * 0.22                       # keeps neighbouring segments apart
    mid = h / 2
    hlen = w - t - gap * 2               # length of a horizontal bar
    vlen = mid - t * 0.5 - gap * 2       # length of a vertical bar

    segs = {
        "a": _hseg(t / 2 + gap, t / 2, hlen, t),
        "d": _hseg(t / 2 + gap, h - t / 2, hlen, t),
        "g": _hseg(t / 2 + gap, mid, hlen, t),
        "f": _vseg(t / 2, t / 2 + gap, vlen, t),
        "b": _vseg(w - t / 2, t / 2 + gap, vlen, t),
        "e": _vseg(t / 2, mid + t / 2 + gap, vlen, t),
        "c": _vseg(w - t / 2, mid + t / 2 + gap, vlen, t),
    }
    active = _SEG_MAP.get(ch, "")
    p.setPen(Qt.NoPen)
    for key, pts in segs.items():
        path = QPainterPath()
        path.moveTo(r.left() + pts[0][0], r.top() + pts[0][1])
        for x, y in pts[1:]:
            path.lineTo(r.left() + x, r.top() + y)
        path.closeSubpath()
        p.setBrush(QBrush(on if key in active else off))
        p.drawPath(path)


def face_led(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    hh, mm, ss, ap = _time_parts(ctx)
    txt = f"{hh}:{mm}" + (f":{ss}" if ctx.show_seconds else "")
    show_date = ctx.settings.get("show_date", True)

    area = QRectF(r)
    if show_date:
        area.setHeight(r.height() * 0.76)

    digits = list(txt)
    n_dig = sum(1 for c in digits if c != ":")
    n_col = sum(1 for c in digits if c == ":")
    gap_ratio, colon_ratio = 0.18, 0.45
    ampm_on = not ctx.hour24 and ctx.settings.get("show_ampm", True)

    # width coefficient in units of one digit width (incl. the AM/PM column)
    k = n_dig * (1 + gap_ratio) + n_col * (colon_ratio + gap_ratio) + (0.9 if ampm_on else 0.0)
    unit = min(area.width() / k, area.height() / 1.9)
    dh = unit * 1.9
    total = unit * k
    x = area.left() + (area.width() - total) / 2
    y = area.top() + (area.height() - dh) / 2

    on = ctx.color("fg")
    off = ctx.color("fg", 0.08)
    blink = ctx.settings.get("blink_colon", False) and ctx.sub_second > 0.5

    for ch in digits:
        if ch == ":":
            cw = unit * colon_ratio
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(ctx.color("accent") if not blink else off))
            d = unit * 0.14
            p.drawEllipse(QPointF(x + cw / 2, y + dh * 0.34), d, d)
            p.drawEllipse(QPointF(x + cw / 2, y + dh * 0.68), d, d)
            x += cw + unit * gap_ratio
        else:
            _draw_seg_digit(p, QRectF(x, y, unit, dh), ch, on, off, unit * 0.16)
            x += unit * (1 + gap_ratio)

    if ampm_on:
        _fit_text(p, QRectF(x, y, unit * 0.9, dh * 0.42), ap,
                  ctx.font(dh * 0.20, 700), ctx.color("accent"), Qt.AlignLeft | Qt.AlignTop)

    if show_date:
        dr = QRectF(r.left(), area.bottom(), r.width(), r.height() * 0.22)
        label = _date_text(ctx)
        if ctx.settings.get("show_label", True) and ctx.label:
            label = f"{ctx.label.upper()}   ·   {label}"
        _fit_text(p, dr, label, ctx.font(dr.height() * 0.72, 400), ctx.color("dim"))


# ---------------------------------------------------------------------------
# 3. Analog
# ---------------------------------------------------------------------------

def _analog_base(p: QPainter, r: QRectF, ctx: FaceContext, style: str) -> None:
    side = min(r.width(), r.height())
    cx, cy = r.center().x(), r.center().y()
    rad = side / 2 * 0.94
    p.save()
    p.translate(cx, cy)

    fg, accent, dim = ctx.color("fg"), ctx.color("accent"), ctx.color("dim")
    bgp = ctx.settings.get("background", "none")

    # dial
    if style in ("classic", "roman"):
        if bgp == "none":
            grad = QRadialGradient(QPointF(0, 0), rad)
            grad.setColorAt(0.0, ctx.color("bg", 0.35))
            grad.setColorAt(1.0, ctx.color("bg", 0.65))
            p.setBrush(QBrush(grad))
        else:
            p.setBrush(Qt.NoBrush)
        p.setPen(QPen(ctx.color("fg", 0.35), max(1.0, rad * 0.015)))
        p.drawEllipse(QPointF(0, 0), rad, rad)

    # ticks
    def tick(a: float, r1: float, r2: float, pen: QPen):
        path = QPainterPath()
        path.moveTo(QPointF(math.sin(a) * r1, -math.cos(a) * r1))
        path.lineTo(QPointF(math.sin(a) * r2, -math.cos(a) * r2))
        draw_shape_fx(p, path, pen)

    if style != "minimal":
        for i in range(60):
            ang = math.radians(i * 6)
            major = i % 5 == 0
            ln = rad * (0.10 if major else 0.045)
            tick(ang, rad - ln, rad * 0.96,
                 QPen(fg if major else dim,
                      max(1.0, rad * (0.022 if major else 0.009)), Qt.SolidLine, Qt.RoundCap))
    else:
        for i in range(12):
            ang = math.radians(i * 30)
            tick(ang, rad * 0.86, rad * 0.96,
                 QPen(fg if i % 3 == 0 else dim, max(1.0, rad * 0.03), Qt.SolidLine, Qt.RoundCap))

    # numerals
    if style in ("classic", "roman"):
        roman = ["XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
        f = ctx.font(rad * 0.20, 500)
        for i in range(12):
            ang = math.radians(i * 30)
            rr = rad * 0.76
            x, y = math.sin(ang) * rr, -math.cos(ang) * rr
            txt = roman[i] if style == "roman" else str(12 if i == 0 else i)
            box = QRectF(x - rad * 0.22, y - rad * 0.16, rad * 0.44, rad * 0.32)
            draw_path_fx(p, _text_path(box, txt, f, Qt.AlignHCenter | Qt.AlignVCenter), fg)

    # label / date inside the dial
    # Keep text inside the hand-free band so it never collides with the numerals.
    inner = 0.45 if style in ("classic", "roman") else 0.70
    if ctx.settings.get("show_label", True) and ctx.label:
        _fit_text(p, QRectF(-rad * inner, -rad * 0.42, rad * inner * 2, rad * 0.17),
                  ctx.label.upper(), ctx.font(rad * 0.12, 600), ctx.color("accent", 0.95))
    if ctx.settings.get("show_date", True):
        _fit_text(p, QRectF(-rad * inner, rad * 0.26, rad * inner * 2, rad * 0.17),
                  _date_text(ctx), ctx.font(rad * 0.11, 400), dim)

    # hands
    n = ctx.now
    sec = n.second + (ctx.sub_second if ctx.smooth else 0.0)
    minute = n.minute + sec / 60.0
    hour = (n.hour % 12) + minute / 60.0

    def hand(angle_deg: float, length: float, width: float, color: QColor, tail: float = 0.18):
        p.save()
        p.rotate(angle_deg)
        path = QPainterPath()
        path.moveTo(QPointF(0, rad * tail))
        path.lineTo(QPointF(0, -rad * length))
        draw_shape_fx(p, path, QPen(color, max(1.2, width), Qt.SolidLine, Qt.RoundCap))
        p.restore()

    hand(hour * 30, 0.52, rad * 0.055, fg, 0.16)
    hand(minute * 6, 0.76, rad * 0.038, fg, 0.18)
    if ctx.show_seconds:
        hand(sec * 6, 0.86, rad * 0.014, accent, 0.22)

    cap = QPainterPath()
    cap.addEllipse(QPointF(0, 0), rad * 0.035, rad * 0.035)
    draw_path_fx(p, cap, fg)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(accent))
    p.drawEllipse(QPointF(0, 0), rad * 0.016, rad * 0.016)
    p.restore()


def face_analog(p, r, ctx):        _analog_base(p, r, ctx, "classic")
def face_analog_minimal(p, r, ctx): _analog_base(p, r, ctx, "minimal")
def face_analog_roman(p, r, ctx):   _analog_base(p, r, ctx, "roman")


# ---------------------------------------------------------------------------
# 4. Flip clock
# ---------------------------------------------------------------------------

def face_flip(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    hh, mm, ss, ap = _time_parts(ctx)
    groups = [hh, mm] + ([ss] if ctx.show_seconds else [])
    show_date = ctx.settings.get("show_date", True)

    area = QRectF(r)
    if show_date:
        area.setHeight(r.height() * 0.78)

    gap = area.width() * 0.03
    cw = (area.width() - gap * (len(groups) - 1)) / len(groups)
    ch = min(area.height(), cw * 1.05)
    y = area.top() + (area.height() - ch) / 2
    x = area.left()

    fg, accent = ctx.color("fg"), ctx.color("accent")
    card_top = ctx.color("bg", 0.92)
    card_bot = QColor(card_top)
    card_bot.setAlphaF(0.78)

    for g in groups:
        rect = QRectF(x, y, cw, ch)
        path = QPainterPath()
        path.addRoundedRect(rect, ch * 0.10, ch * 0.10)
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.0, card_top)
        grad.setColorAt(0.49, card_bot)
        grad.setColorAt(0.51, card_top)
        grad.setColorAt(1.0, card_bot)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)
        # hinge line
        p.setPen(QPen(QColor(0, 0, 0, 120), max(1.0, ch * 0.012)))
        p.drawLine(QPointF(rect.left() + ch * 0.06, rect.center().y()),
                   QPointF(rect.right() - ch * 0.06, rect.center().y()))
        _fit_text(p, rect, g, ctx.font(ch * 0.72, 600), fg, Qt.AlignCenter, 0.82)
        x += cw + gap

    if not ctx.hour24 and ctx.settings.get("show_ampm", True):
        _fit_text(p, QRectF(area.right() - cw * 0.4, y, cw * 0.4, ch * 0.3),
                  ap, ctx.font(ch * 0.16, 700), accent, Qt.AlignRight | Qt.AlignTop)

    if show_date:
        dr = QRectF(r.left(), area.bottom(), r.width(), r.height() * 0.20)
        label = _date_text(ctx)
        if ctx.settings.get("show_label", True) and ctx.label:
            label = f"{ctx.label.upper()}   ·   {label}"
        _fit_text(p, dr, label, ctx.font(dr.height() * 0.70, 400), ctx.color("dim"))


# ---------------------------------------------------------------------------
# 5. Ring / progress clock
# ---------------------------------------------------------------------------

def face_rings(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    side = min(r.width(), r.height())
    cx, cy = r.center().x(), r.center().y()
    rad = side / 2 * 0.94
    n = ctx.now
    sec = n.second + (ctx.sub_second if ctx.smooth else 0.0)

    fracs = [
        ((n.hour % 12) + n.minute / 60) / 12.0,
        (n.minute + sec / 60) / 60.0,
        sec / 60.0,
    ]
    colors = [ctx.color("fg"), ctx.color("accent"), ctx.color("dim")]
    widths = [rad * 0.10, rad * 0.075, rad * 0.045]
    radii = [rad * 0.92, rad * 0.76, rad * 0.63]
    count = 3 if ctx.show_seconds else 2

    p.save()
    p.translate(cx, cy)
    for i in range(count):
        rr = radii[i]
        box = QRectF(-rr, -rr, rr * 2, rr * 2)
        p.setPen(QPen(ctx.color("fg", 0.10), widths[i], Qt.SolidLine, Qt.FlatCap))
        p.drawArc(box, 0, 360 * 16)
        p.setPen(QPen(colors[i], widths[i], Qt.SolidLine, Qt.RoundCap))
        p.drawArc(box, 90 * 16, int(-fracs[i] * 360 * 16))
    p.restore()

    hh, mm, ss, ap = _time_parts(ctx)
    inner = QRectF(cx - rad * 0.52, cy - rad * 0.34, rad * 1.04, rad * 0.44)
    _fit_text(p, inner, f"{hh}:{mm}", ctx.font(rad * 0.40, 300), ctx.color("fg"))
    sub = []
    if ctx.settings.get("show_label", True) and ctx.label:
        sub.append(ctx.label.upper())
    if not ctx.hour24 and ctx.settings.get("show_ampm", True):
        sub.append(ap)
    if sub:
        _fit_text(p, QRectF(cx - rad * 0.5, cy + rad * 0.12, rad, rad * 0.16),
                  "  ".join(sub), ctx.font(rad * 0.13, 500), ctx.color("accent", 0.9))
    if ctx.settings.get("show_date", True):
        _fit_text(p, QRectF(cx - rad * 0.6, cy + rad * 0.30, rad * 1.2, rad * 0.16),
                  _date_text(ctx), ctx.font(rad * 0.11, 400), ctx.color("dim"))


# ---------------------------------------------------------------------------
# 6. Text clock ("quarter past nine")
# ---------------------------------------------------------------------------

_ONES = ["twelve", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve"]
_MINS = {0: "o'clock", 15: "quarter past", 30: "half past", 45: "quarter to"}


def _spell_minute(m: int) -> str:
    words = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
             "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
             "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = {20: "twenty", 30: "thirty", 40: "forty", 50: "fifty"}
    if m < 20:
        return words[m]
    t = (m // 10) * 10
    return tens[t] + ("" if m % 10 == 0 else "-" + words[m % 10])


def face_text(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    n = ctx.now
    m, h = n.minute, n.hour % 12
    if m == 0:
        line1, line2 = _ONES[h], "o'clock"
    elif m in _MINS:
        line1 = _MINS[m]
        line2 = _ONES[(h + 1) % 12] if m == 45 else _ONES[h]
    elif m < 30:
        line1 = f"{_spell_minute(m)} past"
        line2 = _ONES[h]
    else:
        line1 = f"{_spell_minute(60 - m)} to"
        line2 = _ONES[(h + 1) % 12]

    rows = 2 + (1 if ctx.settings.get("show_date", True) else 0)
    rh = r.height() / (rows + 0.2)
    _fit_text(p, QRectF(r.left(), r.top(), r.width(), rh), line1,
              ctx.font(rh * 0.82, 200), ctx.color("dim"), Qt.AlignLeft | Qt.AlignVCenter)
    _fit_text(p, QRectF(r.left(), r.top() + rh, r.width(), rh), line2,
              ctx.font(rh * 0.95, 500), ctx.color("fg"), Qt.AlignLeft | Qt.AlignVCenter)
    if rows == 3:
        extra = _date_text(ctx)
        if ctx.settings.get("show_label", True) and ctx.label:
            extra = f"{ctx.label.upper()}  ·  {extra}"
        _fit_text(p, QRectF(r.left(), r.top() + rh * 2, r.width(), rh * 0.8), extra,
                  ctx.font(rh * 0.42, 400), ctx.color("accent", 0.8),
                  Qt.AlignLeft | Qt.AlignVCenter)


# ---------------------------------------------------------------------------
# 7. Binary clock
# ---------------------------------------------------------------------------

def face_binary(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    n = ctx.now
    cols = [n.hour // 10, n.hour % 10, n.minute // 10, n.minute % 10]
    if ctx.show_seconds:
        cols += [n.second // 10, n.second % 10]
    area = QRectF(r)
    if ctx.settings.get("show_date", True):
        area.setHeight(r.height() * 0.80)

    gap_x = area.width() * 0.02
    cw = (area.width() - gap_x * (len(cols) - 1)) / len(cols)
    rows = 4
    cell = min(cw, area.height() / rows)
    total_w = cell * len(cols) + gap_x * (len(cols) - 1)
    x0 = area.left() + (area.width() - total_w) / 2
    y0 = area.top() + (area.height() - cell * rows) / 2
    rad = cell * 0.34

    on, off = ctx.color("accent"), ctx.color("fg", 0.12)
    p.setPen(Qt.NoPen)
    for ci, val in enumerate(cols):
        for bit in range(rows):
            weight = 8 >> bit
            cx = x0 + ci * (cell + gap_x) + cell / 2
            cy = y0 + bit * cell + cell / 2
            p.setBrush(QBrush(on if val & weight else off))
            p.drawEllipse(QPointF(cx, cy), rad, rad)

    if ctx.settings.get("show_date", True):
        hh, mm, ss, _ = _time_parts(ctx)
        txt = f"{hh}:{mm}" + (f":{ss}" if ctx.show_seconds else "")
        if ctx.label:
            txt = f"{ctx.label.upper()}  {txt}"
        _fit_text(p, QRectF(r.left(), area.bottom(), r.width(), r.height() * 0.18),
                  txt, ctx.font(r.height() * 0.14, 400), ctx.color("dim"))


# ---------------------------------------------------------------------------
# 8. Bar clock (horizontal progress of the day)
# ---------------------------------------------------------------------------

def face_bars(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    n = ctx.now
    sec = n.second + (ctx.sub_second if ctx.smooth else 0.0)
    items = [("H", (n.hour + n.minute / 60) / 24.0, ctx.color("fg")),
             ("M", (n.minute + sec / 60) / 60.0, ctx.color("accent")),
             ("S", sec / 60.0, ctx.color("dim"))]
    if not ctx.show_seconds:
        items = items[:2]

    hh, mm, ss, ap = _time_parts(ctx)
    head = QRectF(r.left(), r.top(), r.width(), r.height() * 0.46)
    txt = f"{hh}:{mm}" + (f":{ss}" if ctx.show_seconds else "")
    _fit_text(p, head, txt, ctx.font(head.height() * 0.95, 300), ctx.color("fg"),
              Qt.AlignLeft | Qt.AlignVCenter)
    if ctx.label and ctx.settings.get("show_label", True):
        _fit_text(p, head, ctx.label.upper(), ctx.font(head.height() * 0.26, 500),
                  ctx.color("accent", 0.85), Qt.AlignRight | Qt.AlignTop)

    bar_area = QRectF(r.left(), r.top() + r.height() * 0.50, r.width(), r.height() * 0.46)
    bh = bar_area.height() / (len(items) * 1.8)
    y = bar_area.top()
    for _, frac, col in items:
        bg = QRectF(bar_area.left(), y, bar_area.width(), bh)
        path = QPainterPath(); path.addRoundedRect(bg, bh / 2, bh / 2)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(ctx.color("fg", 0.10))); p.drawPath(path)
        fillw = max(bh, bg.width() * frac)
        fp = QPainterPath(); fp.addRoundedRect(QRectF(bg.left(), y, fillw, bh), bh / 2, bh / 2)
        p.setBrush(QBrush(col)); p.drawPath(fp)
        y += bh * 1.8


# ---------------------------------------------------------------------------
# Trading session rendering
# ---------------------------------------------------------------------------

def _session_list(ctx: FaceContext):
    if ctx.sessions is not None:
        return ctx.sessions
    return []


def _draw_pills(p: QPainter, r: QRectF, ctx: FaceContext, sts: List) -> None:
    """A row of rounded session badges: name, state dot and countdown."""
    if not sts:
        return
    n = len(sts)
    gap = r.width() * 0.015
    pw = (r.width() - gap * (n - 1)) / n
    ph = min(r.height(), pw * 0.52)
    y = r.top() + (r.height() - ph) / 2
    x = r.left()
    show_cd = ctx.settings.get("session_countdown", True)

    for st in sts:
        col = QColor(st.session.color)
        rect = QRectF(x, y, pw, ph)
        path = QPainterPath(); path.addRoundedRect(rect, ph * 0.32, ph * 0.32)

        bg = QColor(col)
        bg.setAlphaF(0.22 if st.is_open else 0.07)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(bg)); p.drawPath(path)
        edge = QColor(col); edge.setAlphaF(0.95 if st.is_open else 0.22)
        p.setPen(QPen(edge, max(1.0, ph * 0.045))); p.setBrush(Qt.NoBrush); p.drawPath(path)

        # progress bar along the bottom of an open pill
        if st.is_open and st.progress > 0:
            p.save(); p.setClipPath(path)
            fill = QColor(col); fill.setAlphaF(0.30)
            p.setPen(Qt.NoPen); p.setBrush(QBrush(fill))
            p.drawRect(QRectF(rect.left(), rect.bottom() - ph * 0.14,
                              rect.width() * st.progress, ph * 0.14))
            p.restore()

        # status dot
        dot_r = ph * 0.10
        dcx = rect.left() + ph * 0.34
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(col if st.is_open else ctx.color("dim", 0.5)))
        p.drawEllipse(QPointF(dcx, rect.center().y() - (ph * 0.13 if show_cd else 0)), dot_r, dot_r)

        text_rect = QRectF(dcx + dot_r * 2, rect.top(), rect.right() - dcx - dot_r * 2.6,
                           ph * (0.58 if show_cd else 1.0))
        if show_cd:
            text_rect.moveTop(rect.top() + ph * 0.10)
        name_col = ctx.color("fg") if st.is_open else ctx.color("dim")
        _fit_text(p, text_rect, st.session.short, ctx.font(ph * 0.34, 700), name_col,
                  Qt.AlignLeft | Qt.AlignVCenter)

        if show_cd:
            cd = QRectF(rect.left() + ph * 0.22, rect.top() + ph * 0.52,
                        rect.width() - ph * 0.44, ph * 0.36)
            txt = st.countdown_text
            _fit_text(p, cd, txt, ctx.font(ph * 0.28, 400),
                      col if st.is_open else ctx.color("dim", 0.8),
                      Qt.AlignLeft | Qt.AlignVCenter)
        x += pw + gap


def _draw_timeline(p: QPainter, r: QRectF, ctx: FaceContext, sts: List) -> None:
    """A 24-hour UTC ribbon with one lane per session and a 'now' marker."""
    from . import sessions as S
    if not sts or ctx.now_utc is None:
        return
    lanes = len(sts)
    label_w = r.width() * 0.11
    track = QRectF(r.left() + label_w, r.top(), r.width() - label_w, r.height() * 0.80)
    lane_h = track.height() / max(1, lanes)
    bar_h = lane_h * 0.60

    # hour grid
    p.setPen(QPen(ctx.color("fg", 0.08), 1.0))
    for h in range(0, 25, 3):
        x = track.left() + track.width() * h / 24.0
        p.drawLine(QPointF(x, track.top()), QPointF(x, track.bottom()))

    for i, st in enumerate(sts):
        cy = track.top() + lane_h * i + lane_h / 2
        _fit_text(p, QRectF(r.left(), cy - lane_h * 0.4, label_w - 4, lane_h * 0.8),
                  st.session.short, ctx.font(lane_h * 0.42, 700),
                  ctx.color("fg") if st.is_open else ctx.color("dim"),
                  Qt.AlignRight | Qt.AlignVCenter)
        base = QRectF(track.left(), cy - bar_h / 2, track.width(), bar_h)
        bp = QPainterPath(); bp.addRoundedRect(base, bar_h / 2, bar_h / 2)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(ctx.color("fg", 0.07))); p.drawPath(bp)

        col = QColor(st.session.color)
        for a, b in S.day_spans_utc(st.session, ctx.now_utc):
            x1 = track.left() + track.width() * a / 24.0
            x2 = track.left() + track.width() * b / 24.0
            seg = QRectF(x1, cy - bar_h / 2, max(2.0, x2 - x1), bar_h)
            sp = QPainterPath(); sp.addRoundedRect(seg, bar_h / 2, bar_h / 2)
            c = QColor(col); c.setAlphaF(0.95 if st.is_open else 0.45)
            p.setBrush(QBrush(c)); p.drawPath(sp)

    # now marker
    nu = ctx.now_utc
    frac = (nu.hour + nu.minute / 60 + nu.second / 3600) / 24.0
    nx = track.left() + track.width() * frac
    p.setPen(QPen(ctx.color("accent"), max(1.5, r.height() * 0.012)))
    p.drawLine(QPointF(nx, track.top()), QPointF(nx, track.bottom()))
    p.setPen(Qt.NoPen); p.setBrush(QBrush(ctx.color("accent")))
    p.drawEllipse(QPointF(nx, track.top()), r.height() * 0.025, r.height() * 0.025)

    # hour scale
    scale = QRectF(track.left(), track.bottom(), track.width(), r.height() * 0.18)
    f = ctx.font(scale.height() * 0.78, 400)
    p.setFont(f); p.setPen(QPen(ctx.color("dim")))
    for h in range(0, 25, 6):
        x = track.left() + track.width() * h / 24.0
        box = QRectF(x - 20, scale.top(), 40, scale.height())
        if box.left() < track.left():          # keep "00" off the row labels
            box.moveLeft(track.left())
        if box.right() > track.right():        # keep "24" inside the widget
            box.moveRight(track.right())
        p.drawText(box, Qt.AlignCenter, f"{h:02d}")
    _fit_text(p, QRectF(r.left(), scale.top(), label_w - 4, scale.height()), "UTC",
              ctx.font(scale.height() * 0.70, 600), ctx.color("dim", 0.8),
              Qt.AlignRight | Qt.AlignVCenter)


def _draw_session_rows(p: QPainter, r: QRectF, ctx: FaceContext, sts: List) -> None:
    """A compact table: name | OPEN/CLOSED | local hours | countdown."""
    if not sts:
        return
    rh = r.height() / len(sts)
    for i, st in enumerate(sts):
        row = QRectF(r.left(), r.top() + rh * i, r.width(), rh)
        col = QColor(st.session.color)
        if st.is_open:
            bgc = QColor(col); bgc.setAlphaF(0.12)
            bp = QPainterPath(); bp.addRoundedRect(row.adjusted(0, rh * 0.06, 0, -rh * 0.06),
                                                   rh * 0.2, rh * 0.2)
            p.setPen(Qt.NoPen); p.setBrush(QBrush(bgc)); p.drawPath(bp)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(col if st.is_open else ctx.color("dim", 0.35)))
        p.drawEllipse(QPointF(row.left() + rh * 0.34, row.center().y()), rh * 0.11, rh * 0.11)

        fnt = ctx.font(rh * 0.46, 600 if st.is_open else 400)
        tc = ctx.color("fg") if st.is_open else ctx.color("dim")
        _fit_text(p, QRectF(row.left() + rh * 0.62, row.top(), row.width() * 0.30, rh),
                  st.session.name, fnt, tc, Qt.AlignLeft | Qt.AlignVCenter)
        _fit_text(p, QRectF(row.left() + row.width() * 0.40, row.top(), row.width() * 0.26, rh),
                  f"{st.session.short if False else ''}{st.local_open}–{st.local_close}",
                  ctx.font(rh * 0.38, 400), ctx.color("dim"), Qt.AlignLeft | Qt.AlignVCenter)
        _fit_text(p, QRectF(row.left() + row.width() * 0.66, row.top(), row.width() * 0.14, rh),
                  st.state_text, ctx.font(rh * 0.34, 700),
                  col if st.is_open else ctx.color("dim", 0.7), Qt.AlignLeft | Qt.AlignVCenter)
        _fit_text(p, QRectF(row.left() + row.width() * 0.80, row.top(), row.width() * 0.20 - 4, rh),
                  st.countdown_text, ctx.font(rh * 0.40, 500),
                  ctx.color("accent") if st.is_open else ctx.color("dim"),
                  Qt.AlignRight | Qt.AlignVCenter)


def draw_sessions(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    style = ctx.settings.get("session_style", "pills")
    sts = _session_list(ctx)
    if style == "timeline":
        _draw_timeline(p, r, ctx, sts)
    elif style == "list":
        _draw_session_rows(p, r, ctx, sts)
    else:
        _draw_pills(p, r, ctx, sts)


# ---------------------------------------------------------------------------
# 11. Trader dashboard
# ---------------------------------------------------------------------------

def face_trader(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    sts = _session_list(ctx)
    hh, mm, ss, ap = _time_parts(ctx)

    head_h = r.height() * (0.46 if sts else 0.70)
    head = QRectF(r.left(), r.top(), r.width(), head_h)

    txt = f"{hh}:{mm}" + (f":{ss}" if ctx.show_seconds else "")
    tw = head.width() * 0.56
    _fit_text(p, QRectF(head.left(), head.top(), tw, head.height()), txt,
              ctx.font(head.height() * 0.95, int(ctx.settings.get("font_weight", 300))),
              ctx.color("fg"), Qt.AlignLeft | Qt.AlignVCenter)

    # right hand info block: label / UTC time / date
    info = QRectF(head.left() + tw, head.top(), head.width() - tw, head.height())
    lines = []
    if ctx.settings.get("show_label", True) and ctx.label:
        lines.append((ctx.label.upper(), ctx.color("accent"), 0.30, 700))
    if ctx.now_utc is not None:
        lines.append((ctx.now_utc.strftime("UTC %H:%M"), ctx.color("fg", 0.85), 0.26, 500))
    if ctx.settings.get("show_date", True):
        lines.append((_date_text(ctx), ctx.color("dim"), 0.22, 400))
    if not ctx.hour24 and ctx.settings.get("show_ampm", True):
        lines.insert(0, (ap, ctx.color("accent"), 0.26, 700))
    if lines:
        lh = info.height() / len(lines)
        for i, (t, c, sz, wgt) in enumerate(lines):
            _fit_text(p, QRectF(info.left(), info.top() + lh * i, info.width(), lh), t,
                      ctx.font(head.height() * sz, wgt), c, Qt.AlignRight | Qt.AlignVCenter)

    if not sts:
        return

    # overlap banner
    from . import sessions as S
    body_top = head.bottom() + r.height() * 0.02
    names = S.overlaps(sts)
    if names and ctx.settings.get("highlight_overlap", True):
        bh = r.height() * 0.13
        bar = QRectF(r.left(), body_top, r.width(), bh)
        bp = QPainterPath(); bp.addRoundedRect(bar, bh * 0.35, bh * 0.35)
        c = QColor("#FFB300"); c.setAlphaF(0.18)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c)); p.drawPath(bp)
        _fit_text(p, bar, f"OVERLAP  ·  {' + '.join(names)}",
                  ctx.font(bh * 0.60, 700), QColor("#FFC247"), Qt.AlignCenter)
        body_top += bh + r.height() * 0.02

    draw_sessions(p, QRectF(r.left(), body_top, r.width(), r.bottom() - body_top), ctx)


# ---------------------------------------------------------------------------
# 12. Session timeline only
# ---------------------------------------------------------------------------

def face_session_timeline(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    hh, mm, ss, _ap = _time_parts(ctx)
    head = QRectF(r.left(), r.top(), r.width(), r.height() * 0.30)
    txt = f"{hh}:{mm}" + (f":{ss}" if ctx.show_seconds else "")
    _fit_text(p, head, txt, ctx.font(head.height() * 0.95, 300), ctx.color("fg"),
              Qt.AlignLeft | Qt.AlignVCenter)
    if ctx.now_utc is not None:
        _fit_text(p, head, ctx.now_utc.strftime("UTC %H:%M:%S"),
                  ctx.font(head.height() * 0.40, 500), ctx.color("dim"),
                  Qt.AlignRight | Qt.AlignVCenter)
    body = QRectF(r.left(), head.bottom() + r.height() * 0.04, r.width(),
                  r.height() * 0.62)
    _draw_timeline(p, body, ctx, _session_list(ctx))


# ---------------------------------------------------------------------------
# 13. Session board (big list)
# ---------------------------------------------------------------------------

def face_session_board(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    sts = _session_list(ctx)
    head = QRectF(r.left(), r.top(), r.width(), r.height() * 0.24)
    hh, mm, ss, _ = _time_parts(ctx)
    _fit_text(p, head, f"{hh}:{mm}:{ss}" if ctx.show_seconds else f"{hh}:{mm}",
              ctx.font(head.height() * 0.92, 300), ctx.color("fg"),
              Qt.AlignLeft | Qt.AlignVCenter)
    from . import sessions as S
    names = S.overlaps(sts)
    right = f"OVERLAP {' + '.join(names)}" if names else _date_text(ctx)
    _fit_text(p, head, right, ctx.font(head.height() * 0.34, 600),
              QColor("#FFC247") if names else ctx.color("dim"),
              Qt.AlignRight | Qt.AlignVCenter)
    _draw_session_rows(p, QRectF(r.left(), head.bottom() + 4, r.width(),
                                 r.bottom() - head.bottom() - 4), ctx, sts)


# ---------------------------------------------------------------------------
# 14. World clock rows (multi timezone)
# ---------------------------------------------------------------------------

def face_world(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    from . import timezones as TZ
    zones = ctx.settings.get("world_zones") or ["Asia/Dhaka", "Europe/London", "America/New_York"]
    if ctx.now_utc is None:
        return
    rh = r.height() / max(1, len(zones))
    for i, z in enumerate(zones):
        row = QRectF(r.left(), r.top() + rh * i, r.width(), rh)
        t = TZ.localize(ctx.now_utc, z)
        name = TZ.city_label(z)
        _fit_text(p, QRectF(row.left(), row.top(), row.width() * 0.44, rh), name,
                  ctx.font(rh * 0.46, 500), ctx.color("dim"), Qt.AlignLeft | Qt.AlignVCenter)
        tt = t.strftime("%H:%M" if ctx.hour24 else "%I:%M %p")
        _fit_text(p, QRectF(row.left() + row.width() * 0.44, row.top(), row.width() * 0.38, rh),
                  tt, ctx.font(rh * 0.62, 400), ctx.color("fg"),
                  Qt.AlignRight | Qt.AlignVCenter)
        _fit_text(p, QRectF(row.left() + row.width() * 0.84, row.top(), row.width() * 0.16, rh),
                  TZ.offset_label(z).replace("UTC", ""), ctx.font(rh * 0.32, 400),
                  ctx.color("accent", 0.8), Qt.AlignRight | Qt.AlignVCenter)



# ---------------------------------------------------------------------------
# NEW in 1.5 - extra faces
# ---------------------------------------------------------------------------

def face_stack(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    """Huge hours above huge minutes - very readable from across the room."""
    hh, mm, ss, ap = _time_parts(ctx)
    show_date = ctx.settings.get("show_date", True)
    foot = r.height() * (0.16 if show_date else 0.0)
    body = QRectF(r.left(), r.top(), r.width(), r.height() - foot)
    half = body.height() / 2.0
    f1 = ctx.font(half * 1.02, int(ctx.settings.get("font_weight", 300)))
    _draw_glow_text(p, QRectF(body.left(), body.top(), body.width(), half), hh,
                    _shrink_to_fit(f1, hh, QRectF(0, 0, body.width() * 0.9, half)),
                    ctx.color("fg"), ctx.color("glow"), 1.0, Qt.AlignCenter)
    _draw_glow_text(p, QRectF(body.left(), body.top() + half, body.width(), half), mm,
                    _shrink_to_fit(f1, mm, QRectF(0, 0, body.width() * 0.9, half)),
                    ctx.color("accent"), ctx.color("glow"), 1.0, Qt.AlignCenter)
    if ctx.show_seconds:
        sr = QRectF(body.right() - body.width() * 0.22, body.center().y() - half * 0.18,
                    body.width() * 0.20, half * 0.36)
        _fit_text(p, sr, ss, ctx.font(half * 0.26, 400), ctx.color("dim"),
                  Qt.AlignRight | Qt.AlignVCenter)
    if not ctx.hour24 and ctx.settings.get("show_ampm", True):
        ar = QRectF(body.left(), body.center().y() - half * 0.18,
                    body.width() * 0.20, half * 0.36)
        _fit_text(p, ar, ap, ctx.font(half * 0.24, 700), ctx.color("accent", 0.9),
                  Qt.AlignLeft | Qt.AlignVCenter)
    if show_date:
        _fit_text(p, QRectF(r.left(), body.bottom(), r.width(), foot), _date_text(ctx),
                  ctx.font(foot * 0.80, 400), ctx.color("dim"))


def face_arc_dial(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    """A single wide arc gauge with the time written inside it."""
    side = min(r.width(), r.height() * 1.6)
    cx, cy = r.center().x(), r.top() + min(r.height() * 0.92, side * 0.56)
    rad = side * 0.46
    n = ctx.now
    sec = n.second + (ctx.sub_second if ctx.smooth else 0.0)
    frac = ((n.hour % 12) * 3600 + n.minute * 60 + sec) / 43200.0
    box = QRectF(cx - rad, cy - rad, rad * 2, rad * 2)
    w = max(3.0, rad * 0.13)
    p.setPen(QPen(ctx.color("fg", 0.12), w, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(box, 200 * 16, -220 * 16)
    p.setPen(QPen(ctx.color("accent"), w, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(box, 200 * 16, int(-220 * 16 * frac))
    # minute ring inside
    inner = QRectF(cx - rad * 0.76, cy - rad * 0.76, rad * 1.52, rad * 1.52)
    w2 = max(2.0, rad * 0.06)
    p.setPen(QPen(ctx.color("fg", 0.10), w2, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(inner, 200 * 16, -220 * 16)
    p.setPen(QPen(ctx.color("fg", 0.65), w2, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(inner, 200 * 16, int(-220 * 16 * ((n.minute + sec / 60.0) / 60.0)))

    hh, mm, ss, ap = _time_parts(ctx)
    txt = f"{hh}:{mm}"
    _fit_text(p, QRectF(cx - rad * 0.62, cy - rad * 0.30, rad * 1.24, rad * 0.56),
              txt, ctx.font(rad * 0.52, int(ctx.settings.get("font_weight", 300))),
              ctx.color("fg"))
    sub = []
    if ctx.show_seconds:
        sub.append(ss)
    if not ctx.hour24 and ctx.settings.get("show_ampm", True):
        sub.append(ap)
    if ctx.settings.get("show_label", True) and ctx.label:
        sub.append(ctx.label.upper())
    if sub:
        _fit_text(p, QRectF(cx - rad * 0.7, cy + rad * 0.28, rad * 1.4, rad * 0.20),
                  "  ·  ".join(sub), ctx.font(rad * 0.16, 500), ctx.color("accent", 0.9))
    if ctx.settings.get("show_date", True):
        _fit_text(p, QRectF(cx - rad * 0.9, cy + rad * 0.52, rad * 1.8, rad * 0.18),
                  _date_text(ctx), ctx.font(rad * 0.13, 400), ctx.color("dim"))


def face_neon(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    """Hollow neon-tube lettering - looks great on a photo wallpaper."""
    hh, mm, ss, ap = _time_parts(ctx)
    colon = ":"
    if ctx.settings.get("blink_colon", False) and ctx.sub_second > 0.5:
        colon = " "
    text = f"{hh}{colon}{mm}" + (f"{colon}{ss}" if ctx.show_seconds else "")
    show_date = ctx.settings.get("show_date", True)
    foot = r.height() * (0.18 if show_date else 0.0)
    body = QRectF(r.left(), r.top(), r.width(), r.height() - foot)
    f = _shrink_to_fit(ctx.font(body.height() * 0.92, 400), text,
                       QRectF(0, 0, body.width() * 0.92, body.height()))
    path = _text_path(body, text, f, Qt.AlignHCenter | Qt.AlignVCenter)
    glow = QColor(ctx.pal.get("glow", ctx.pal.get("accent", "#38E1C6")))
    lw = max(2.0, body.height() * 0.035)
    p.setBrush(Qt.NoBrush)
    for i, mul in enumerate((4.2, 2.6, 1.6)):
        c = QColor(glow); c.setAlphaF(0.10 + i * 0.10)
        p.setPen(QPen(c, lw * mul, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)
    pen = QPen(ctx.color("fg"), lw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    if _fxb("gradient_on", False):
        pen.setBrush(_fill_brush(path, ctx.color("fg")))
    p.setPen(pen)
    p.drawPath(path)
    if not ctx.hour24 and ctx.settings.get("show_ampm", True):
        _fit_text(p, QRectF(body.right() - body.width() * 0.16, body.top() + body.height() * 0.12,
                            body.width() * 0.15, body.height() * 0.3),
                  ap, ctx.font(body.height() * 0.22, 700), ctx.color("accent"),
                  Qt.AlignRight | Qt.AlignTop)
    if show_date:
        _fit_text(p, QRectF(r.left(), body.bottom(), r.width(), foot), _date_text(ctx),
                  ctx.font(foot * 0.72, 400), ctx.color("dim"))


def face_minimal(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    """Ultra-clean: just the time, wide letter spacing, nothing else."""
    hh, mm, ss, ap = _time_parts(ctx)
    text = f"{hh} {mm}" + (f" {ss}" if ctx.show_seconds else "")
    f = ctx.font(r.height() * 0.9, int(ctx.settings.get("font_weight", 200)))
    f.setLetterSpacing(QFont.PercentageSpacing, 112)
    _draw_glow_text(p, r, text, _shrink_to_fit(f, text, QRectF(0, 0, r.width() * 0.94, r.height())),
                    ctx.color("fg"), ctx.color("glow"), 1.0, Qt.AlignCenter)


def face_ticker(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    """A thin one-line strip: time · date · zone. Perfect along a screen edge."""
    hh, mm, ss, ap = _time_parts(ctx)
    t = f"{hh}:{mm}" + (f":{ss}" if ctx.show_seconds else "")
    if not ctx.hour24 and ctx.settings.get("show_ampm", True):
        t += " " + ap
    h = r.height()
    x = r.left() + h * 0.25
    tw = r.width() * 0.42
    _fit_text(p, QRectF(x, r.top(), tw, h), t, ctx.font(h * 0.78, 400),
              ctx.color("fg"), Qt.AlignLeft | Qt.AlignVCenter)
    rest = []
    if ctx.settings.get("show_label", True) and ctx.label:
        rest.append(ctx.label.upper())
    if ctx.settings.get("show_date", True):
        rest.append(_date_text(ctx))
    if rest:
        _fit_text(p, QRectF(r.left() + tw, r.top(), r.width() - tw - h * 0.25, h),
                  "   ·   ".join(rest), ctx.font(h * 0.40, 400), ctx.color("dim"),
                  Qt.AlignRight | Qt.AlignVCenter)


def face_dots(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    """Dot-matrix style: each digit column shown as a stack of lit dots."""
    n = ctx.now
    vals = [(n.hour if ctx.hour24 else (n.hour % 12 or 12)), n.minute]
    maxv = [24 if ctx.hour24 else 12, 60]
    if ctx.show_seconds:
        vals.append(n.second); maxv.append(60)
    cols = len(vals)
    pad = min(r.width(), r.height()) * 0.08
    area = r.adjusted(pad, pad, -pad, -pad)
    cw = area.width() / cols
    steps = 12
    for i, (v, mx) in enumerate(zip(vals, maxv)):
        lit = int(round(v / mx * steps))
        col = ctx.color("fg") if i == 0 else (ctx.color("accent") if i == 1 else ctx.color("dim"))
        d = min(cw * 0.42, area.height() / steps * 0.72)
        cx = area.left() + cw * (i + 0.5)
        for k in range(steps):
            cy = area.bottom() - (k + 0.5) * (area.height() / steps)
            c = QColor(col)
            c.setAlphaF(1.0 if k < lit else 0.13)
            p.setPen(Qt.NoPen); p.setBrush(QBrush(c))
            p.drawEllipse(QPointF(cx, cy), d / 2, d / 2)
        _fit_text(p, QRectF(cx - cw * 0.5, area.bottom(), cw, pad * 0.95),
                  f"{v:02d}", ctx.font(pad * 0.85, 500), col)


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

FACES: Dict[str, Callable[[QPainter, QRectF, FaceContext], None]] = {
    "digital": face_digital,
    "led": face_led,
    "analog": face_analog,
    "analog_minimal": face_analog_minimal,
    "analog_roman": face_analog_roman,
    "flip": face_flip,
    "rings": face_rings,
    "text": face_text,
    "binary": face_binary,
    "bars": face_bars,
    "trader": face_trader,
    "session_timeline": face_session_timeline,
    "session_board": face_session_board,
    "world": face_world,
    "stack": face_stack,
    "arc_dial": face_arc_dial,
    "neon": face_neon,
    "minimal": face_minimal,
    "ticker": face_ticker,
    "dots": face_dots,
}

FACE_LABELS = {
    "digital": "Digital (classic)",
    "led": "LED seven-segment",
    "analog": "Analog (numbers)",
    "analog_minimal": "Analog (minimal)",
    "analog_roman": "Analog (roman)",
    "flip": "Flip cards",
    "rings": "Rings / progress",
    "text": "Word clock",
    "binary": "Binary",
    "bars": "Bars",
    "trader": "Trader dashboard  ★",
    "session_timeline": "Session timeline (24h)  ★",
    "session_board": "Session board  ★",
    "world": "World clock (multi zone)",
    "stack": "Stacked (hours over minutes)",
    "arc_dial": "Arc gauge",
    "neon": "Neon tube",
    "minimal": "Minimal (time only)",
    "ticker": "Ticker strip (one line)",
    "dots": "Dot matrix",
}

# faces that need the trading-session data
SESSION_FACES = {"trader", "session_timeline", "session_board"}

# faces that look best in a square window
SQUARE_FACES = {"analog", "analog_minimal", "analog_roman", "rings", "dots"}


def render(painter: QPainter, rect: QRectF, ctx: FaceContext) -> None:
    set_fx(ctx.settings, ctx.pal, ctx.quality)
    key = ctx.settings.get("face", "digital")
    fn = FACES.get(key, face_digital)

    # Any ordinary face can carry a session strip underneath it.
    strip = None
    if key not in SESSION_FACES and ctx.settings.get("show_sessions", False) and ctx.sessions:
        style = ctx.settings.get("session_style", "pills")
        frac = {"pills": 0.26, "timeline": 0.40, "list": 0.46}.get(style, 0.26)
        h = rect.height() * frac
        strip = QRectF(rect.left(), rect.bottom() - h, rect.width(), h)
        rect = QRectF(rect.left(), rect.top(), rect.width(), rect.height() - h - rect.height() * 0.02)

    painter.save()
    try:
        fn(painter, rect, ctx)
    finally:
        painter.restore()

    if strip is not None:
        painter.save()
        try:
            draw_sessions(painter, strip, ctx)
        finally:
            painter.restore()
