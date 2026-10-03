"""Aurora Clock - alert, alarm and chime engine.

Handles three kinds of events:
  * session alerts  - "London opens in 15 minutes", "New York just closed"
  * custom alarms   - one-shot, daily, weekdays-only or weekly
  * chimes          - every hour / half hour / quarter

Notifications are delivered through the tray balloon, an optional on-screen
banner and an optional sound.  Nothing here blocks the UI thread.
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

import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Optional

from . import sessions
from .timezones import get_zone

REPEAT_MODES = ["once", "daily", "weekdays", "weekly"]


def default_alarm() -> dict:
    return {
        "id": "",
        "enabled": True,
        "label": "Alarm",
        "time": "09:00",            # HH:MM
        "timezone": "",             # empty = the clock's / system zone
        "repeat": "daily",          # once | daily | weekdays | weekly
        "weekday": 0,               # used by "weekly"
        "sound": "chime",
        "notify": True,
        "banner": True,
        "last_fired": "",           # ISO date(-time) guard against double fire
    }


# ---------------------------------------------------------------------------
# sound
# ---------------------------------------------------------------------------

SOUNDS = {
    "none":   None,
    "beep":   [(880, 120)],
    "chime":  [(1046, 140), (1318, 140), (1568, 220)],
    "alert":  [(1200, 90), (0, 60), (1200, 90), (0, 60), (1200, 160)],
    "bell":   [(1568, 90), (1318, 90), (1046, 260)],
    "soft":   [(660, 180), (880, 240)],
}


def play_sound(name: str) -> None:
    """Non-blocking tone sequence. Falls back to the system beep elsewhere."""
    seq = SOUNDS.get(name)
    if not seq:
        return

    def _run():
        try:
            if sys.platform == "win32":
                import winsound
                for freq, dur in seq:
                    if freq <= 0:
                        import time as _t
                        _t.sleep(dur / 1000.0)
                    else:
                        winsound.Beep(int(freq), int(dur))
            else:
                sys.stdout.write("\a")
                sys.stdout.flush()
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# engine
# ---------------------------------------------------------------------------

@dataclass
class Notification:
    title: str
    body: str
    color: str = "#38E1C6"
    sound: str = "chime"
    banner: bool = True


class AlertEngine:
    """Polled once per second by the app; emits Notification objects."""

    def __init__(self, cfg, timesync):
        self.cfg = cfg
        self.timesync = timesync
        self.on_notify: Optional[Callable[[Notification], None]] = None
        self._fired: Dict[str, str] = {}      # key -> marker, prevents repeats
        self._prev_open: Dict[str, bool] = {}  # session key -> previous state
        self._prev_overlap: str = ""
        self._warmed = False

    def warm_up(self) -> None:
        """Record the current state once at start-up so the app does not fire
        'London just opened' the moment you log in to an already-open market."""
        now_utc = self.timesync.now_utc()
        keys = self.cfg.data.get("sessions", {}).get("enabled", sessions.DEFAULT_ENABLED)
        sts = sessions.statuses(keys, now_utc)
        for st in sts:
            self._prev_open[st.session.key] = st.is_open
        self._prev_overlap = "+".join(sorted(sessions.overlaps(sts)))
        self._warmed = True

    # -- public ------------------------------------------------------------
    def tick(self) -> None:
        now_utc = self.timesync.now_utc()
        try:
            self._check_sessions(now_utc)
            self._check_alarms(now_utc)
            self._check_chimes(now_utc)
        except Exception:
            pass

    # -- sessions ----------------------------------------------------------
    def _check_sessions(self, now_utc: datetime) -> None:
        cfg = self.cfg.alerts
        if not cfg.get("sessions_enabled", True):
            return
        lead = int(cfg.get("lead_minutes", 15))
        keys = self.cfg.data.get("sessions", {}).get("enabled", sessions.DEFAULT_ENABLED)

        sts = sessions.statuses(keys, now_utc)

        for st in sts:
            s = st.session
            # ---- pre-open warning -------------------------------------
            if cfg.get("notify_pre_open", True) and not st.is_open and st.opens_in is not None:
                mins = st.opens_in.total_seconds() / 60.0
                if lead - 0.6 <= mins <= lead + 0.6:
                    self._fire(f"preopen:{s.key}:{st.next_open}",
                               Notification(f"{s.name} opens soon",
                                            f"{s.name} opens in {lead} minutes "
                                            f"({st.local_open} your time).",
                                            s.color, cfg.get("sound_session", "soft")))

            # ---- open / close transitions -----------------------------
            prev = self._prev_open.get(s.key)
            if prev is not None and prev != st.is_open:
                if st.is_open and cfg.get("notify_open", True):
                    self._emit(Notification(
                        f"{s.name} is OPEN",
                        f"The {s.name} session just opened "
                        f"({st.local_open} – {st.local_close} your time).",
                        s.color, cfg.get("sound_session", "chime")))
                elif not st.is_open and cfg.get("notify_close", True):
                    nxt = f"Next open in {sessions.fmt_delta(st.opens_in)}." if st.opens_in else ""
                    self._emit(Notification(
                        f"{s.name} is CLOSED",
                        f"The {s.name} session just closed. {nxt}".strip(),
                        s.color, cfg.get("sound_session", "soft")))
            self._prev_open[s.key] = st.is_open

        # ---- overlap window --------------------------------------------
        if cfg.get("notify_overlap", True):
            names = sessions.overlaps(sts)
            marker = "+".join(sorted(names))
            if len(names) >= 2 and marker != self._prev_overlap:
                self._fire(f"overlap:{marker}:{now_utc.date()}",
                           Notification("Session overlap",
                                        f"{' + '.join(names)} are open together — "
                                        "expect higher volatility and volume.",
                                        "#FFB300", cfg.get("sound_session", "alert")))
            self._prev_overlap = marker

    # -- alarms ------------------------------------------------------------
    def _check_alarms(self, now_utc: datetime) -> None:
        for al in self.cfg.data.get("alarms", []):
            if not al.get("enabled", True):
                continue
            zone = get_zone(al.get("timezone", "")) if al.get("timezone") else None
            now = now_utc.astimezone(zone) if zone else now_utc.astimezone()
            try:
                hh, mm = [int(x) for x in str(al.get("time", "09:00")).split(":")[:2]]
            except ValueError:
                continue
            if now.hour != hh or now.minute != mm:
                continue

            rep = al.get("repeat", "daily")
            if rep == "weekdays" and now.weekday() > 4:
                continue
            if rep == "weekly" and now.weekday() != int(al.get("weekday", 0)):
                continue

            marker = now.strftime("%Y-%m-%d %H:%M")
            if al.get("last_fired") == marker:
                continue
            al["last_fired"] = marker
            if rep == "once":
                al["enabled"] = False
            self.cfg.save()
            self._emit(Notification(al.get("label") or "Alarm",
                                    f"Alarm at {al.get('time')}"
                                    + (f" ({al['timezone']})" if al.get("timezone") else ""),
                                    "#FF6B6B", al.get("sound", "chime"),
                                    bool(al.get("banner", True))))

    # -- chimes ------------------------------------------------------------
    def _check_chimes(self, now_utc: datetime) -> None:
        cfg = self.cfg.alerts
        mode = cfg.get("chime", "off")
        if mode == "off":
            return
        now = now_utc.astimezone()
        trigger = {"hour": now.minute == 0,
                   "half": now.minute in (0, 30),
                   "quarter": now.minute in (0, 15, 30, 45)}.get(mode, False)
        if not trigger:
            return
        if cfg.get("chime_quiet_hours", True) and (now.hour >= 22 or now.hour < 7):
            return
        self._fire(f"chime:{now:%Y-%m-%d %H:%M}",
                   Notification("Time check", now.strftime("It is %I:%M %p"),
                                "#8FA6B8", cfg.get("sound_chime", "soft"),
                                bool(cfg.get("chime_banner", False))))

    # -- plumbing ----------------------------------------------------------
    def _fire(self, key: str, note: Notification) -> None:
        if self._fired.get(key):
            return
        self._fired[key] = "1"
        if len(self._fired) > 400:
            self._fired = dict(list(self._fired.items())[-200:])
        self._emit(note)

    def _emit(self, note: Notification) -> None:
        if note.sound:
            play_sound(note.sound)
        cb = self.on_notify
        if cb:
            try:
                cb(note)
            except Exception:
                pass
