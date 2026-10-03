"""Aurora Clock - application controller (tray icon, clock manager)."""
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

import copy
import sys
from typing import Dict, Optional

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from . import alerts as AL
from . import autostart, fonts, themes, winutil
from . import sessions as S
from .banner import Banner
from .config import APP_DISPLAY_NAME, APP_VERSION, Config
from .overlay import ClockOverlay
from .settings_ui import SettingsDialog
from .timesync import TimeSync


class _ShellEventFilter(QAbstractNativeEventFilter):
    """Catches the broadcast Explorer sends when it restarts.

    Without this the clock silently loses its place in the Z order (or its
    tray icon) whenever Explorer crashes, is restarted from Task Manager, or
    the user refreshes the desktop.
    """

    def __init__(self, app_ctx):
        super().__init__()
        self.app = app_ctx
        self.msg_id = winutil.taskbar_created_message()

    def nativeEventFilter(self, event_type, message):
        if self.msg_id and event_type == b"windows_generic_MSG":
            try:
                from ctypes import wintypes
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == self.msg_id:
                    QTimer.singleShot(1200, self.app.recover_after_shell_restart)
                    QTimer.singleShot(4000, self.app.recover_after_shell_restart)
            except Exception:
                pass
        return False, 0


def make_icon(size: int = 64) -> QIcon:
    """Draw the tray icon at runtime so the app stays a single dependency-free file set."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pal = themes.THEMES["aurora"]
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(pal["bg"]))
    p.drawEllipse(2, 2, size - 4, size - 4)
    from PySide6.QtGui import QPen
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(pal["accent"]), max(2, size // 16)))
    p.drawEllipse(4, 4, size - 8, size - 8)
    p.setPen(QPen(QColor(pal["fg"]), max(2, size // 14), Qt.SolidLine, Qt.RoundCap))
    c = size / 2
    p.drawLine(QPoint(int(c), int(c)), QPoint(int(c), int(c - size * 0.26)))
    p.drawLine(QPoint(int(c), int(c)), QPoint(int(c + size * 0.20), int(c)))
    p.end()
    return QIcon(pm)


class AuroraApp(QObject):
    def __init__(self, qapp: QApplication, start_hidden_ui: bool = True):
        super().__init__()
        self.qapp = qapp
        self.cfg = Config()
        fonts.load_all(self.cfg)
        self.timesync = TimeSync(self.cfg)
        self.timesync.on_update = self._on_time_update
        self.overlays: Dict[str, ClockOverlay] = {}
        self.alerts = AL.AlertEngine(self.cfg, self.timesync)
        self.alerts.on_notify = self._on_notification
        self._banners: list = []
        self._session_cache: Dict[str, tuple] = {}
        self.settings_dialog: Optional[SettingsDialog] = None
        self.icon = make_icon()
        qapp.setWindowIcon(self.icon)

        self._build_tray()
        self._build_overlays()

        # first run: enable autostart as the user expects a set-and-forget app
        if self.cfg.data.get("first_run", True):
            if self.cfg.general.get("autostart", True):
                autostart.set_autostart(True)
            self.cfg.data["first_run"] = False
            self.cfg.save()
            if self.tray and self.tray.isVisible():
                self.tray.showMessage(
                    APP_DISPLAY_NAME,
                    "Running in the tray. Drag the clock anywhere, right-click it for options.",
                    self.icon, 6000)

        self.timesync.start()

        # keep the overlays alive through anything Windows throws at them
        self._shell_filter = _ShellEventFilter(self)
        try:
            qapp.installNativeEventFilter(self._shell_filter)
        except Exception:
            pass

        period = max(1, int(self.cfg.general.get("watchdog_seconds", 2))) * 1000
        self._watchdog = QTimer(self)
        self._watchdog.timeout.connect(self._watchdog_tick)
        self._watchdog.start(period)

        # re-assert once more a few seconds after launch: at login we often
        # start before Explorer has finished creating the desktop
        for delay in (1500, 4000, 9000, 20000):
            QTimer.singleShot(delay, self.recover_after_shell_restart)

        # alert engine: one tick per second is plenty and costs nothing
        self.alerts.warm_up()
        self._alert_timer = QTimer(self)
        self._alert_timer.timeout.connect(self.alerts.tick)
        self._alert_timer.start(1000)

        # watch for screen changes so clocks never end up off-screen
        QGuiApplication.instance().screenAdded.connect(lambda _s: self.refresh_all())
        QGuiApplication.instance().screenRemoved.connect(lambda _s: self.refresh_all())

        if not start_hidden_ui:
            self.open_settings()

    # ------------------------------------------------------------ watchdog --
    def _watchdog_tick(self) -> None:
        """Cheap, runs every couple of seconds."""
        if not self.act_show.isChecked():
            return
        fullscreen = False
        if sys.platform == "win32":
            own = [winutil.hwnd_of(w) for w in self.overlays.values()]
            fullscreen = winutil.foreground_is_fullscreen(own)
        for cid, w in self.overlays.items():
            c = self.cfg.clock_by_id(cid)
            if not c:
                continue
            want = bool(c.get("enabled", True))
            if want and fullscreen and c.get("hide_when_fullscreen", True):
                want = False
            if w._should_be_visible != want:
                w.set_should_be_visible(want)
            elif want:
                w.watchdog()

    def restart_watchdog(self) -> None:
        period = max(1, int(self.cfg.general.get("watchdog_seconds", 3))) * 1000
        self._watchdog.start(period)

    def recover_after_shell_restart(self) -> None:
        """Re-create the tray icon and force every clock back into place."""
        try:
            if self.cfg.general.get("show_tray_icon", True):
                self.tray.hide()
                self.tray.show()
        except Exception:
            pass
        for cid, w in self.overlays.items():
            c = self.cfg.clock_by_id(cid)
            if c and c.get("enabled", True) and self.act_show.isChecked():
                w._wallpaper_parented = False     # WorkerW is gone after a restart
                w.set_should_be_visible(True)
                w.apply_settings()

    # ------------------------------------------------------------ sessions --
    def session_keys_for(self, clock: dict) -> list:
        keys = clock.get("session_keys") or self.cfg.sessions_cfg.get("enabled") \
            or S.DEFAULT_ENABLED
        return [k for k in keys if k in S.CATALOGUE]

    def session_statuses(self, clock: dict):
        """Computed at most once per second per key set, then shared."""
        keys = self.session_keys_for(clock)
        now_utc = self.timesync.now_utc()
        stamp = int(now_utc.timestamp())
        ck = "|".join(keys) + "|" + clock.get("timezone", "")
        cached = self._session_cache.get(ck)
        if cached and cached[0] == stamp:
            return cached[1]
        sts = S.statuses(keys, now_utc, clock.get("timezone", ""))
        sort = self.cfg.sessions_cfg.get("sort", "time")
        if sort == "name":
            sts.sort(key=lambda x: x.session.name)
        elif sort == "open_first":
            sts.sort(key=lambda x: (not x.is_open, x.session.name))
        self._session_cache[ck] = (stamp, sts)
        return sts

    # ------------------------------------------------------------ overlays --
    def _build_overlays(self) -> None:
        for c in self.cfg.clocks:
            self._create_overlay(c)

    def _create_overlay(self, c: dict) -> ClockOverlay:
        w = ClockOverlay(c, self)
        w.changed.connect(self._on_clock_changed)
        w.request_settings.connect(self.open_settings)
        w.request_remove.connect(self.remove_clock)
        w.request_duplicate.connect(self.duplicate_clock)
        self.overlays[c["id"]] = w
        if c.get("enabled", True):
            w.set_should_be_visible(True)
        else:
            w.set_should_be_visible(False)
        return w

    def _on_clock_changed(self, _cid: str) -> None:
        self.cfg.save()
        if self.settings_dialog:
            self.settings_dialog._load_fields()

    def refresh_clock(self, cid: str) -> None:
        c = self.cfg.clock_by_id(cid)
        w = self.overlays.get(cid)
        if not c or not w:
            return
        w.s = c
        w.apply_settings()
        w.set_should_be_visible(bool(c.get("enabled", True)) and self.act_show.isChecked())

    def refresh_all(self) -> None:
        for cid in list(self.overlays):
            self.refresh_clock(cid)

    def add_clock(self) -> dict:
        c = self.cfg.new_clock(f"Clock {len(self.cfg.clocks) + 1}")
        c["x"] += 40 * len(self.cfg.clocks)
        c["y"] += 40 * len(self.cfg.clocks)
        c["locked"] = bool(self.cfg.general.get("lock_by_default", True))
        self.cfg.clocks.append(c)
        self.cfg.save()
        self._create_overlay(c)
        return c

    def duplicate_clock(self, cid: str) -> dict:
        src = self.cfg.clock_by_id(cid)
        if not src:
            return self.add_clock()
        c = copy.deepcopy(src)
        c["id"] = self.cfg.new_clock()["id"]
        c["name"] = src["name"] + " copy"
        c["x"] += 30; c["y"] += 30
        self.cfg.clocks.append(c)
        self.cfg.save()
        self._create_overlay(c)
        return c

    def remove_clock(self, cid: str, ask: bool = False) -> None:
        if len(self.cfg.clocks) <= 1:
            # Only explain this when a human actually clicked Delete; a
            # programmatic call must never pop a modal dialog.
            if ask:
                QMessageBox.information(None, APP_DISPLAY_NAME,
                                        "At least one clock must remain.\n"
                                        "You can hide it instead: tray icon → Clocks → "
                                        "untick “Show this clock”.")
            return
        if ask:
            c = self.cfg.clock_by_id(cid)
            name = c.get("name", cid) if c else cid
            if QMessageBox.question(
                    None, APP_DISPLAY_NAME,
                    f"Delete the clock “{name}”?\n\nThis cannot be undone.",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
        w = self.overlays.pop(cid, None)
        if w:
            w.close(); w.deleteLater()
        self.cfg.data["clocks"] = [c for c in self.cfg.clocks if c["id"] != cid]
        self.cfg.save()

    def snap(self, cid: str, where: str) -> None:
        c = self.cfg.clock_by_id(cid)
        w = self.overlays.get(cid)
        if not c or not w:
            return
        sc = w.screen() or QGuiApplication.primaryScreen()
        a = sc.availableGeometry()
        m = int(c.get("snap_margin", 24))
        g = QRect(a.left() + m, a.top() + m, c["width"], c["height"])
        horiz = where[-1] if len(where) > 1 else where
        vert = where[0] if len(where) > 1 else where
        # horizontal
        if horiz == "r":
            g.moveRight(a.right() - m)
        elif horiz in ("c", "l") and where in ("tc", "bc", "c"):
            g.moveLeft(a.left() + (a.width() - g.width()) // 2)
        elif horiz == "l":
            g.moveLeft(a.left() + m)
        if where in ("cl",):
            g.moveLeft(a.left() + m)
        if where in ("cr",):
            g.moveRight(a.right() - m)
        # vertical
        if vert == "b":
            g.moveBottom(a.bottom() - m)
        elif vert == "c" or where in ("cl", "cr", "c"):
            g.moveTop(a.top() + (a.height() - g.height()) // 2)
        else:
            g.moveTop(a.top() + m)
        if where == "c":
            g.moveCenter(a.center())
        c["x"], c["y"] = g.x(), g.y()
        self.cfg.save()
        self.refresh_clock(cid)

    # -------------------------------------------------------- notifications --
    def _on_notification(self, note) -> None:
        cfg = self.cfg.alerts
        if cfg.get("tray_balloon", True) and self.tray.isVisible():
            self.tray.showMessage(note.title, note.body, self.icon,
                                  int(cfg.get("banner_seconds", 7)) * 1000)
        if note.banner:
            b = Banner(note.title, note.body, note.color,
                       int(cfg.get("banner_seconds", 7)))
            b.pop()
            self._banners = [x for x in self._banners if x.isVisible()][-4:] + [b]

    def test_notification(self) -> None:
        self._on_notification(AL.Notification(
            "Aurora Clock", "This is how an alert will look and sound.",
            "#38E1C6", self.cfg.alerts.get("sound_session", "chime")))

    # --------------------------------------------------------------- tray --
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.icon)
        self.tray.setToolTip(f"{APP_DISPLAY_NAME} {APP_VERSION}")
        menu = QMenu()

        a = QAction("Settings…", menu); a.triggered.connect(lambda: self.open_settings())
        menu.addAction(a)
        a = QAction("Add a clock", menu); a.triggered.connect(lambda: self.add_clock())
        menu.addAction(a)
        menu.addSeparator()

        self.act_show = QAction("Show all clocks", menu, checkable=True)
        self.act_show.setChecked(True)
        self.act_show.triggered.connect(self.toggle_all)
        menu.addAction(self.act_show)

        self.act_lock = QAction("Lock all clocks", menu, checkable=True)
        self.act_lock.triggered.connect(self.lock_all)
        menu.addAction(self.act_lock)

        self.act_edit = QAction("Edit mode (unlock dragging)", menu, checkable=True)
        self.act_edit.setChecked(bool(self.cfg.general.get("edit_mode", False)))
        self.act_edit.triggered.connect(self.set_edit_mode)
        menu.addAction(self.act_edit)

        self.clocks_menu = menu.addMenu("Clocks")
        self.clocks_menu.aboutToShow.connect(self._rebuild_clocks_menu)

        layer_menu = menu.addMenu("Screen layer")
        self._layer_actions = {}
        for k in (winutil.Z_TOP, winutil.Z_NORMAL, winutil.Z_BOTTOM, winutil.Z_DESKTOP):
            a = QAction(winutil.Z_LABELS[k].split(" — ")[0], layer_menu, checkable=True)
            a.triggered.connect(lambda _c, kk=k: self.set_layer_all(kk))
            layer_menu.addAction(a)
            self._layer_actions[k] = a
        a = QAction("Bring all clocks back now", menu)
        a.setToolTip("Force every clock back on screen and into the right layer")
        a.triggered.connect(self.recover_after_shell_restart)
        menu.addAction(a)

        self.act_alerts = QAction("Session alerts", menu, checkable=True)
        self.act_alerts.setChecked(bool(self.cfg.alerts.get("sessions_enabled", True)))
        self.act_alerts.triggered.connect(self.set_session_alerts)
        menu.addAction(self.act_alerts)

        menu.addSeparator()
        a = QAction("Sync time now", menu); a.triggered.connect(self.timesync.sync_now)
        menu.addAction(a)
        self.act_status = QAction("Time: not synced yet", menu); self.act_status.setEnabled(False)
        menu.addAction(self.act_status)
        menu.addSeparator()
        a = QAction("Quit", menu); a.triggered.connect(self.quit)
        menu.addAction(a)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.update_tray_visibility()

    def update_tray_visibility(self) -> None:
        if self.cfg.general.get("show_tray_icon", True) and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        else:
            self.tray.hide()

    def _tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.open_settings()

    def _on_time_update(self) -> None:
        st = self.timesync.status
        if st["synced"]:
            self.act_status.setText(f"Time synced · offset {st['offset_ms']:+.0f} ms")
        else:
            self.act_status.setText("Time: using system clock")

    # ------------------------------------------------------------ actions --
    def toggle_all(self, show: bool) -> None:
        for cid, w in self.overlays.items():
            c = self.cfg.clock_by_id(cid)
            w.set_should_be_visible(bool(show and c and c.get("enabled", True)))

    def set_edit_mode(self, on: bool) -> None:
        self.cfg.general["edit_mode"] = bool(on)
        self.cfg.save()
        if hasattr(self, "act_edit"):
            self.act_edit.setChecked(bool(on))
        self.refresh_all()
        if on and self.tray.isVisible():
            self.tray.showMessage(
                "Edit mode ON",
                "You can now drag and resize your clocks. "
                "Turn it off to lock everything in place.", self.icon, 4000)

    def _rebuild_clocks_menu(self) -> None:
        """Always-reachable list of every clock, even when they overlap."""
        m = self.clocks_menu
        m.clear()
        for c in list(self.cfg.clocks):
            sub = m.addMenu(c.get("name", c["id"]))
            a = QAction("Show this clock", sub, checkable=True)
            a.setChecked(bool(c.get("enabled", True)))
            a.triggered.connect(lambda v, cid=c["id"]: self.set_clock_enabled(cid, v))
            sub.addAction(a)
            a = QAction("Settings for this clock…", sub)
            a.triggered.connect(lambda _v, cid=c["id"]: self.open_settings(cid))
            sub.addAction(a)
            a = QAction("Flash it so I can find it", sub)
            a.triggered.connect(lambda _v, cid=c["id"]: self.flash_clock(cid))
            sub.addAction(a)
            sub.addSeparator()
            a = QAction("Move to top-left corner", sub)
            a.triggered.connect(lambda _v, cid=c["id"]: self.snap(cid, "tl"))
            sub.addAction(a)
            a = QAction("Delete this clock", sub)
            a.triggered.connect(lambda _v, cid=c["id"]: self.remove_clock(cid, ask=True))
            sub.addAction(a)
        m.addSeparator()
        a = QAction("Add a clock", m)
        a.triggered.connect(lambda: self.add_clock())
        m.addAction(a)
        if len(self.cfg.clocks) > 1:
            a = QAction("Keep only the first clock (remove the rest)", m)
            a.triggered.connect(self.keep_only_first)
            m.addAction(a)

    def set_clock_enabled(self, cid: str, on: bool) -> None:
        c = self.cfg.clock_by_id(cid)
        if not c:
            return
        c["enabled"] = bool(on)
        self.cfg.save()
        self.refresh_clock(cid)

    def flash_clock(self, cid: str) -> None:
        """Blink a clock three times so the user can tell which is which."""
        w = self.overlays.get(cid)
        if not w:
            return
        seq = [0, 250, 500, 750, 1000, 1250]
        for i, delay in enumerate(seq):
            QTimer.singleShot(delay, lambda vis=(i % 2 == 1), ww=w: ww.setWindowOpacity(
                float(ww.s.get("opacity", 0.92)) if vis else 0.15))
        QTimer.singleShot(1600, lambda ww=w: ww.setWindowOpacity(
            float(ww.s.get("opacity", 0.92))))

    def keep_only_first(self) -> None:
        if len(self.cfg.clocks) <= 1:
            return
        keep = self.cfg.clocks[0]["id"]
        for c in list(self.cfg.clocks):
            if c["id"] != keep:
                self.remove_clock(c["id"], ask=False)

    def set_layer_all(self, mode: str) -> None:
        for c in self.cfg.clocks:
            c["z_mode"] = mode
            c["always_on_top"] = (mode == winutil.Z_TOP)
        self.cfg.save()
        self.refresh_all()
        for k, a in getattr(self, "_layer_actions", {}).items():
            a.setChecked(k == mode)
        if self.tray.isVisible():
            self.tray.showMessage("Aurora Clock",
                                  winutil.Z_LABELS.get(mode, mode), self.icon, 3500)

    def set_session_alerts(self, on: bool) -> None:
        self.cfg.alerts["sessions_enabled"] = bool(on)
        self.cfg.save()

    def lock_all(self, locked: bool) -> None:
        for c in self.cfg.clocks:
            c["locked"] = locked
        self.cfg.save()
        self.refresh_all()

    def open_settings(self, clock_id: str = "", tab: str = "") -> None:
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self, clock_id)
            self.settings_dialog.finished.connect(self._settings_closed)
        if clock_id:
            self.settings_dialog._reload_list(clock_id)
        if tab:
            self.settings_dialog.show_tab(tab)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def _settings_closed(self, *_a) -> None:
        self.cfg.save()
        if self.settings_dialog:
            self.settings_dialog.deleteLater()
            self.settings_dialog = None

    def quit(self) -> None:
        self.cfg.save()
        self.timesync.stop()
        if hasattr(self, "_alert_timer"):
            self._alert_timer.stop()
        if hasattr(self, "_watchdog"):
            self._watchdog.stop()
        self.tray.hide()
        self.qapp.quit()
