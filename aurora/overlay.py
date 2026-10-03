"""Aurora Clock - the frameless always-on-top overlay window."""
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

from typing import Optional

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QCursor,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QMenu, QWidget

from . import contrast, faces, themes, timezones, winutil

RESIZE_MARGIN = 10
MIN_W, MIN_H = 80, 50


class ClockOverlay(QWidget):
    """One floating clock.  Several can exist at once."""

    changed = Signal(str)             # emits clock id when geometry/settings change
    request_settings = Signal(str)
    request_remove = Signal(str)
    request_duplicate = Signal(str)

    def __init__(self, settings: dict, app_ctx, parent=None):
        super().__init__(parent)
        self.s = settings
        self.app = app_ctx            # AuroraApp, provides timesync + config

        self._wallpaper_parented = False
        self._should_be_visible = True
        self._drag_origin: Optional[QPoint] = None
        self._drag_geo: Optional[QRect] = None
        self._resize_edge = ""
        self._hover_edge = ""
        self._hovered = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(600)
        self._save_timer.timeout.connect(lambda: self.changed.emit(self.s["id"]))

        self._init_window()
        self.apply_settings()

        # Adaptive repainting: a digital clock only has to be redrawn when a
        # digit actually changes (once a second), not 25 times a second.  Only
        # a sweeping analog second hand needs real animation.  This is the
        # single biggest CPU saving in the whole application.
        self._last_key = ""
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._tick_check)
        self._tick.start(self._tick_interval())

    # ------------------------------------------------------------ repaint --
    def _needs_animation(self) -> bool:
        s = self.s
        if s.get("seconds_mode", "smooth") != "smooth":
            return False
        if not s.get("show_seconds", True):
            return False
        return s.get("face") in ("analog", "analog_minimal", "analog_roman",
                                 "rings", "bars")

    def _tick_interval(self) -> int:
        perf = self.app.cfg.general.get("performance", "balanced")
        if self._needs_animation():
            return {"low": 100, "balanced": 50, "smooth": 33}.get(perf, 50)
        return {"low": 500, "balanced": 250, "smooth": 150}.get(perf, 250)

    def _content_key(self) -> str:
        """Everything that is visible on screen, as a short string."""
        s = self.s
        now_utc = self.app.timesync.now_utc()
        now = timezones.localize(now_utc, s.get("timezone", ""))
        if s.get("show_seconds", True) and s.get("seconds_mode", "smooth") != "hidden":
            key = now.strftime("%H%M%S")
        else:
            key = now.strftime("%H%M")
        if s.get("blink_colon", False):
            key += "1" if now_utc.microsecond < 500000 else "0"
        if s.get("face") in faces.SESSION_FACES or s.get("show_sessions", False):
            key += "s"          # session countdowns tick every second
        return key

    def _tick_check(self) -> None:
        if not self.isVisible():
            return
        if self._needs_animation():
            self.update()
            return
        key = self._content_key()
        if key != self._last_key:
            self._last_key = key
            self.update()

    def restart_tick(self) -> None:
        self._tick.start(self._tick_interval())

    # ----------------------------------------------------------- locking --
    @property
    def movable(self) -> bool:
        """A clock can only be moved/resized when it is unlocked AND the app
        is in edit mode.  This is what stops an accidental mouse drag from
        ever nudging the clock out of place."""
        if self.s.get("locked", False):
            return False
        if self.s.get("click_through", False):
            return False
        return bool(self.app.cfg.general.get("edit_mode", False))

    # ------------------------------------------------------------------ ui --
    def _init_window(self) -> None:
        flags = Qt.FramelessWindowHint | Qt.Tool | Qt.NoDropShadowWindowHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_AlwaysShowToolTips, True)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.setWindowTitle(f"Aurora Clock – {self.s.get('name', '')}")

    @property
    def z_mode(self) -> str:
        m = self.s.get("z_mode")
        if m in (winutil.Z_TOP, winutil.Z_NORMAL, winutil.Z_BOTTOM, winutil.Z_DESKTOP):
            return m
        return winutil.Z_TOP if self.s.get("always_on_top", True) else winutil.Z_NORMAL

    def apply_settings(self) -> None:
        s = self.s
        mode = self.z_mode

        flags = Qt.FramelessWindowHint | Qt.Tool | Qt.NoDropShadowWindowHint
        if mode == winutil.Z_TOP:
            flags |= Qt.WindowStaysOnTopHint
        elif mode in (winutil.Z_BOTTOM, winutil.Z_DESKTOP):
            # Qt has no "always at the bottom" hint; the native layer does it
            flags |= Qt.WindowDoesNotAcceptFocus
        if flags != self.windowFlags():
            visible = self.isVisible()
            self.setWindowFlags(flags)
            if visible:
                self.show_overlay()

        self.setWindowOpacity(float(s.get("opacity", 0.92)))
        self.setAttribute(Qt.WA_TransparentForMouseEvents, bool(s.get("click_through", False)))
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        g = QRect(int(s["x"]), int(s["y"]), max(MIN_W, int(s["width"])), max(MIN_H, int(s["height"])))
        self.setGeometry(self._clamp_to_screens(g))

        self._apply_native()
        if hasattr(self, "_tick"):
            self.restart_tick()
        self._last_key = ""
        self.update()

    # ------------------------------------------------------- native layer --
    def _apply_native(self) -> None:
        """Push the current settings down to the Win32 window."""
        hwnd = winutil.hwnd_of(self)
        if not hwnd:
            return
        mode = self.z_mode
        winutil.prepare_window(hwnd, bool(self.s.get("click_through", False)))

        want_wallpaper = (mode == winutil.Z_DESKTOP)
        if want_wallpaper and not self._wallpaper_parented:
            g = self.geometry()
            if winutil.attach_to_wallpaper(hwnd):
                self._wallpaper_parented = True
                self.setGeometry(g)          # re-apply after re-parenting
            else:
                # No WorkerW on this system (rare). "Behind every window"
                # gives the user the same practical result.
                mode = winutil.Z_BOTTOM
        elif not want_wallpaper and self._wallpaper_parented:
            winutil.detach_from_wallpaper(hwnd)
            self._wallpaper_parented = False
            g = self.geometry()
            self.setGeometry(g)

        winutil.apply_z_order(hwnd, mode, show=self.isVisible(), force=True)

    def show_overlay(self) -> None:
        """Show without stealing focus, then re-assert the Z order."""
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.show()
        self._apply_native()

    def watchdog(self) -> None:
        """Called by the app a few times a minute.

        Re-asserting the Z order is what keeps the clock alive through an
        Explorer restart, a desktop refresh, Win+D, a resolution change or a
        full-screen game that yanked the topmost band away from us.
        """
        if not self._should_be_visible:
            return
        hwnd = winutil.hwnd_of(self)
        if not hwnd:
            return
        if not self.isVisible():
            self.show_overlay()
            return
        winutil.ensure_visible(hwnd)
        winutil.apply_z_order(hwnd, self.z_mode, show=True, force=False)

    def set_should_be_visible(self, on: bool) -> None:
        self._should_be_visible = bool(on)
        if on:
            self.show_overlay()
        else:
            self.hide()

    @staticmethod
    def _clamp_to_screens(geo: QRect) -> QRect:
        """Keep the clock reachable even if a monitor was unplugged."""
        screens = QGuiApplication.screens()
        if not screens:
            return geo
        for sc in screens:
            if sc.availableGeometry().intersects(geo):
                return geo
        prim = QGuiApplication.primaryScreen().availableGeometry()
        geo.moveTo(prim.left() + 60, prim.top() + 60)
        return geo

    # --------------------------------------------------------------- paint --
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing |
                         QPainter.SmoothPixmapTransform)
        s = self.s
        pal = themes.palette(s.get("theme", "aurora"), s.get("custom_colors"))
        if s.get("fx_auto_contrast", False):
            pal = contrast.adjust(s, pal, self.geometry())
            auto_edge = pal.get("_auto_outline")
            if auto_edge and float(s.get("fx_outline", 0.0)) <= 0.05:
                # give the glyphs an edge even if the user has not set one
                s = dict(s)
                s["fx_outline"] = 1.6
                s["fx_outline_color"] = auto_edge
        rect = QRectF(self.rect())

        # background panel
        bgmode = s.get("background", "none")
        if bgmode != "none":
            radius = float(s.get("corner_radius", 18))
            path = QPainterPath()
            path.addRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)
            col = QColor(pal["bg"])
            base = float(s.get("bg_opacity", 0.45))
            col.setAlphaF(max(0.0, min(1.0, {"panel": base, "glass": base * 0.6,
                                             "solid": 1.0}.get(bgmode, base))))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(col))
            p.drawPath(path)
            if bgmode == "glass":
                edge = QColor(pal["fg"]); edge.setAlphaF(0.18)
                p.setPen(QPen(edge, 1.0)); p.setBrush(Qt.NoBrush); p.drawPath(path)

        # edit affordance while hovered and unlocked
        if self._hovered and self.movable:
            edge = QColor(pal["accent"]); edge.setAlphaF(0.55)
            p.setPen(QPen(edge, 1.0, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

        # edit-mode hint
        if self.app.cfg.general.get("edit_mode", False) and not s.get("locked", False):
            tag = QColor(pal["accent"]); tag.setAlphaF(0.85)
            p.setPen(QPen(tag, 1.0))
            p.setBrush(Qt.NoBrush)
            fnt = p.font(); fnt.setPixelSize(10); p.setFont(fnt)
            p.drawText(rect.adjusted(6, 2, -6, 0), Qt.AlignRight | Qt.AlignTop, "EDIT")

        # the face itself
        now_utc = self.app.timesync.now_utc()
        tz = s.get("timezone", "")
        now = timezones.localize(now_utc, tz)
        sub = (now_utc.microsecond / 1_000_000.0)
        label = s.get("label") or (timezones.city_label(tz) if tz else "")

        sts = None
        if s.get("face") in faces.SESSION_FACES or s.get("show_sessions", False):
            sts = self.app.session_statuses(s)

        pad = 8.0 if bgmode != "none" else 2.0
        ctx = faces.FaceContext(now=now, sub_second=sub, pal=pal, settings=s,
                                label=label, now_utc=now_utc, sessions=sts,
                                quality=self.app.cfg.general.get("performance", "balanced"))
        faces.render(p, rect.adjusted(pad, pad, -pad, -pad), ctx)
        p.end()

    # --------------------------------------------------------------- mouse --
    def _edge_at(self, pos: QPoint) -> str:
        m, r = RESIZE_MARGIN, self.rect()
        edge = ""
        if pos.y() <= m:
            edge += "t"
        elif pos.y() >= r.height() - m:
            edge += "b"
        if pos.x() <= m:
            edge += "l"
        elif pos.x() >= r.width() - m:
            edge += "r"
        return edge

    def _cursor_for(self, edge: str) -> Qt.CursorShape:
        return {
            "t": Qt.SizeVerCursor, "b": Qt.SizeVerCursor,
            "l": Qt.SizeHorCursor, "r": Qt.SizeHorCursor,
            "tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor,
            "tr": Qt.SizeBDiagCursor, "bl": Qt.SizeBDiagCursor,
        }.get(edge, Qt.OpenHandCursor)

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.unsetCursor()
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or not self.movable:
            return super().mousePressEvent(e)
        self._drag_origin = e.globalPosition().toPoint()
        self._drag_geo = self.geometry()
        self._resize_edge = self._edge_at(e.position().toPoint())
        if not self._resize_edge:
            self.setCursor(Qt.ClosedHandCursor)
        e.accept()

    def mouseMoveEvent(self, e):
        if not self.movable:
            return super().mouseMoveEvent(e)
        if self._drag_origin is None:
            edge = self._edge_at(e.position().toPoint())
            if edge != self._hover_edge:
                self._hover_edge = edge
                self.setCursor(QCursor(self._cursor_for(edge)))
            return super().mouseMoveEvent(e)

        delta = e.globalPosition().toPoint() - self._drag_origin
        g = QRect(self._drag_geo)
        if not self._resize_edge:
            g.moveTopLeft(self._drag_geo.topLeft() + delta)
            if e.modifiers() & Qt.ShiftModifier:        # snap to 10 px grid
                g.moveTo(round(g.x() / 10) * 10, round(g.y() / 10) * 10)
            g = self._snap_to_edges(g)
        else:
            if "l" in self._resize_edge:
                g.setLeft(min(g.left() + delta.x(), g.right() - MIN_W))
            if "r" in self._resize_edge:
                g.setRight(max(g.right() + delta.x(), g.left() + MIN_W))
            if "t" in self._resize_edge:
                g.setTop(min(g.top() + delta.y(), g.bottom() - MIN_H))
            if "b" in self._resize_edge:
                g.setBottom(max(g.bottom() + delta.y(), g.top() + MIN_H))
            keep_square = (self.s.get("face") in faces.SQUARE_FACES) or \
                (e.modifiers() & Qt.ControlModifier)
            if keep_square:
                side = max(g.width(), g.height())
                if "l" in self._resize_edge:
                    g.setLeft(g.right() - side)
                else:
                    g.setRight(g.left() + side)
                if "t" in self._resize_edge:
                    g.setTop(g.bottom() - side)
                else:
                    g.setBottom(g.top() + side)
        self.setGeometry(g)
        e.accept()

    def _snap_to_edges(self, g: QRect, threshold: int = 14) -> QRect:
        sc = self.screen() or QGuiApplication.primaryScreen()
        a = sc.availableGeometry()
        if abs(g.left() - a.left()) < threshold:
            g.moveLeft(a.left())
        if abs(g.right() - a.right()) < threshold:
            g.moveRight(a.right())
        if abs(g.top() - a.top()) < threshold:
            g.moveTop(a.top())
        if abs(g.bottom() - a.bottom()) < threshold:
            g.moveBottom(a.bottom())
        return g

    def mouseReleaseEvent(self, e):
        self._drag_origin = None
        self._resize_edge = ""
        self.setCursor(QCursor(self._cursor_for(self._hover_edge)))
        self._persist_geometry()
        e.accept()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.request_settings.emit(self.s["id"])
        e.accept()

    def wheelEvent(self, e):
        """Ctrl + wheel = resize, Alt + wheel = opacity."""
        if not self.movable:
            return
        steps = e.angleDelta().y() / 120.0
        if e.modifiers() & Qt.ControlModifier:
            g = self.geometry()
            factor = 1.0 + steps * 0.06
            nw, nh = max(MIN_W, int(g.width() * factor)), max(MIN_H, int(g.height() * factor))
            g.setRect(g.x(), g.y(), nw, nh)
            self.setGeometry(g)
            self._persist_geometry()
            e.accept()
        elif e.modifiers() & Qt.AltModifier:
            o = min(1.0, max(0.15, self.windowOpacity() + steps * 0.05))
            self.setWindowOpacity(o)
            self.s["opacity"] = o
            self._save_timer.start()
            e.accept()

    def keyPressEvent(self, e):
        if not self.movable:
            return
        step = 10 if e.modifiers() & Qt.ShiftModifier else 1
        dx = {Qt.Key_Left: -step, Qt.Key_Right: step}.get(e.key(), 0)
        dy = {Qt.Key_Up: -step, Qt.Key_Down: step}.get(e.key(), 0)
        if dx or dy:
            self.move(self.x() + dx, self.y() + dy)
            self._persist_geometry()
            e.accept()

    def _persist_geometry(self) -> None:
        g = self.geometry()
        self.s.update({"x": g.x(), "y": g.y(), "width": g.width(), "height": g.height()})
        sc = self.screen()
        if sc:
            self.s["screen"] = sc.name()
        self._save_timer.start()

    # ---------------------------------------------------------------- menu --
    def _show_menu(self, pos: QPoint) -> None:
        m = QMenu(self)
        cid = self.s["id"]

        act = QAction("Settings…", m); act.triggered.connect(lambda: self.request_settings.emit(cid))
        m.addAction(act)

        face_menu = m.addMenu("Clock face")
        for key, lbl in faces.FACE_LABELS.items():
            a = QAction(lbl, face_menu, checkable=True)
            a.setChecked(self.s.get("face") == key)
            a.triggered.connect(lambda _c, k=key: self._set("face", k))
            face_menu.addAction(a)

        theme_menu = m.addMenu("Theme")
        for key, lbl in themes.THEME_LABELS.items():
            a = QAction(lbl, theme_menu, checkable=True)
            a.setChecked(self.s.get("theme") == key)
            a.triggered.connect(lambda _c, k=key: self._set("theme", k))
            theme_menu.addAction(a)

        tz_menu = m.addMenu("Time zone")
        a = QAction("System local time", tz_menu, checkable=True)
        a.setChecked(not self.s.get("timezone"))
        a.triggered.connect(lambda: self._set("timezone", ""))
        tz_menu.addAction(a); tz_menu.addSeparator()
        for z in timezones.POPULAR:
            a = QAction(f"{timezones.city_label(z)}  ({timezones.offset_label(z)})",
                        tz_menu, checkable=True)
            a.setChecked(self.s.get("timezone") == z)
            a.triggered.connect(lambda _c, k=z: self._set("timezone", k))
            tz_menu.addAction(a)

        m.addSeparator()
        a = QAction("Edit mode (allow moving)", m, checkable=True)
        a.setChecked(bool(self.app.cfg.general.get("edit_mode", False)))
        a.triggered.connect(self.app.set_edit_mode)
        m.addAction(a)

        sess = m.addMenu("Trading sessions")
        a = QAction("Show session strip", sess, checkable=True)
        a.setChecked(bool(self.s.get("show_sessions", False)))
        a.triggered.connect(lambda c: self._set("show_sessions", c))
        sess.addAction(a)
        sess.addSeparator()
        for key, lbl in (("pills", "Style: pills"), ("timeline", "Style: 24h timeline"),
                         ("list", "Style: list")):
            a = QAction(lbl, sess, checkable=True)
            a.setChecked(self.s.get("session_style", "pills") == key)
            a.triggered.connect(lambda _c, k=key: self._set("session_style", k))
            sess.addAction(a)
        a = QAction("Show countdowns", sess, checkable=True)
        a.setChecked(bool(self.s.get("session_countdown", True)))
        a.triggered.connect(lambda c: self._set("session_countdown", c))
        sess.addSeparator(); sess.addAction(a)
        a = QAction("Choose sessions…", sess)
        a.triggered.connect(lambda: self.app.open_settings(cid, tab="Sessions"))
        sess.addAction(a)

        for key, text in (("locked", "Lock position && size"),
                          ("click_through", "Click-through (ignore mouse)"),
                          ("always_on_top", "Always on top"),
                          ("show_seconds", "Show seconds"),
                          ("hour24", "24-hour format"),
                          ("show_date", "Show date")):
            a = QAction(text, m, checkable=True)
            a.setChecked(bool(self.s.get(key)))
            a.triggered.connect(lambda checked, k=key: self._set(k, checked))
            m.addAction(a)

        m.addSeparator()
        a = QAction("Duplicate this clock", m)
        a.triggered.connect(lambda: self.request_duplicate.emit(cid)); m.addAction(a)
        a = QAction("Remove this clock", m)
        a.triggered.connect(lambda: self.request_remove.emit(cid)); m.addAction(a)
        m.addSeparator()
        a = QAction("Sync time now", m)
        a.triggered.connect(self.app.timesync.sync_now); m.addAction(a)
        a = QAction("Quit Aurora Clock", m)
        a.triggered.connect(self.app.quit); m.addAction(a)

        m.exec(self.mapToGlobal(pos))

    def _set(self, key: str, value) -> None:
        self.s[key] = value
        self.apply_settings()
        self.changed.emit(self.s["id"])
