"""Aurora Clock - configuration store.

Settings are kept in a single JSON file in the user's AppData folder so that
the application stays fully portable and never needs admin rights.
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

import copy
import json
import os
import sys
import threading
from typing import Any, Dict, List

APP_NAME = "AuroraClock"
APP_DISPLAY_NAME = "Aurora Clock"
APP_VERSION = "1.5.0"


def config_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


CONFIG_PATH = os.path.join(config_dir(), "settings.json")


# --------------------------------------------------------------------------
# Defaults
# --------------------------------------------------------------------------

# Guard against a settings file naming a face that no longer exists.
_KNOWN_FACES = {
    "digital", "led", "analog", "analog_minimal", "analog_roman", "flip",
    "rings", "text", "binary", "bars", "trader", "session_timeline",
    "session_board", "world", "stack", "arc_dial", "neon", "minimal",
    "ticker", "dots",
}


def default_clock(name: str = "Main Clock") -> Dict[str, Any]:
    """A single clock overlay definition."""
    return {
        "id": "",                       # filled in by the manager
        "name": name,
        "enabled": True,

        # --- placement -----------------------------------------------------
        "x": 80,
        "y": 80,
        "width": 420,
        "height": 180,
        "anchor": "free",               # free | top-left | top-right | ...
        "snap_margin": 24,
        "screen": "",                   # empty = primary / remembered
        "locked": False,                # lock position & size
        "click_through": False,         # mouse events pass to window behind
        "always_on_top": False,      # kept for older settings files
        "z_mode": "desktop",         # top | normal | bottom | desktop
        "show_on_all_desktops": True,
        "hide_when_fullscreen": True,   # auto hide over games / video

        # --- appearance ----------------------------------------------------
        "face": "digital",              # see faces.FACES
        "theme": "aurora",              # see themes.THEMES
        "opacity": 0.92,
        "scale": 1.0,
        "font_family": "Segoe UI",
        "font_weight": 300,
        "custom_colors": {},            # overrides on top of the theme
        "background": "none",           # none | panel | glass | solid
        "corner_radius": 18,
        "bg_opacity": 0.45,             # strength of the panel/glass backdrop
        "shadow": True,
        "seconds_mode": "smooth",       # smooth | tick | hidden

        # --- legibility effects (readable on ANY wallpaper) ---------------
        "fx_shadow": True,              # drop shadow behind text & hands
        "fx_shadow_dx": 2.0,
        "fx_shadow_dy": 2.0,
        "fx_shadow_blur": 7.0,          # 0 = hard shadow
        "fx_shadow_opacity": 0.80,
        "fx_shadow_color": "#000000",
        "fx_outline": 0.0,              # stroke width in px (0 = off)
        "fx_outline_color": "#000000",
        "fx_outline_opacity": 0.95,
        "fx_glow": 0.0,                 # 0..1 soft halo in the accent colour
        "fx_glow_color": "",            # empty = theme glow colour
        "fx_plate": False,              # dark/light plate behind the text only
        "fx_plate_opacity": 0.38,
        "fx_plate_color": "#000000",
        "fx_plate_pad": 10.0,
        "fx_plate_radius": 10.0,
        "fx_auto_contrast": False,      # pick light/dark text from the wallpaper
        "fx_auto_strength": 1.0,

        # --- gradient colouring (new in 1.5) ------------------------------
        "gradient_on": False,
        "gradient_preset": "aurora",    # see faces.GRADIENT_PRESETS
        "gradient_c1": "#38E1C6",
        "gradient_c2": "#6C8CFF",
        "gradient_dir": "vertical",     # vertical|vertical_r|horizontal|diagonal|radial
        "gradient_mid": 0.5,
        "gradient_shapes": True,        # also colour analog hands / bars

        # --- content -------------------------------------------------------
        "timezone": "",                 # empty = system local time
        "label": "",                    # empty = auto (city name)
        "show_label": True,
        "hour24": False,
        "show_seconds": True,
        "show_ampm": True,
        "show_date": True,
        "date_format": "dddd, d MMMM yyyy",
        "blink_colon": False,

        # --- trading session panel ----------------------------------------
        "show_sessions": False,         # strip of session pills under the time
        "session_keys": [],             # empty = use the global list
        "session_style": "pills",       # pills | timeline | list
        "session_countdown": True,      # show time to open/close
    }


DEFAULTS: Dict[str, Any] = {
    "version": APP_VERSION,
    "first_run": True,
    "clocks": [],
    "alarms": [],

    "general": {
        "autostart": True,
        "start_minimised": True,
        "show_tray_icon": True,
        "language": "en",
        "confirm_exit": True,
        "global_hotkey_toggle": "Ctrl+Alt+C",
        "performance": "balanced",      # low | balanced | smooth
        "update_interval_ms": 40,       # legacy, kept for old settings files
        "edit_mode": False,             # master unlock: clocks only move in edit mode
        "lock_by_default": True,        # new clocks start locked
        "fade_animations": True,
    },

    "sessions": {
        "enabled": ["sydney", "tokyo", "london", "newyork"],
        "show_closed": True,
        "sort": "time",                 # time | name | open_first
        "highlight_overlap": True,
    },

    "alerts": {
        "sessions_enabled": True,
        "notify_pre_open": True,
        "notify_open": True,
        "notify_close": True,
        "notify_overlap": True,
        "lead_minutes": 15,
        "sound_session": "chime",
        "sound_chime": "soft",
        "chime": "off",                 # off | hour | half | quarter
        "chime_quiet_hours": True,
        "chime_banner": False,
        "banner_seconds": 7,
        "tray_balloon": True,
    },

    "fonts": {
        "custom_files": [],             # user supplied .ttf/.otf paths
    },

    "timesync": {
        "enabled": True,
        "servers": [
            "time.windows.com",
            "pool.ntp.org",
            "time.google.com",
            "time.cloudflare.com",
        ],
        "interval_minutes": 60,
        "timeout_seconds": 3,
        "max_offset_warn_ms": 2000,
        "apply_offset": True,           # correct a wrong system clock in-app
        "last_offset_ms": 0.0,
        "last_sync": "",
        "last_server": "",
    },
}


class Config:
    """Thread-safe JSON-backed settings object."""

    def __init__(self, path: str = CONFIG_PATH):
        self.path = path
        self._lock = threading.RLock()
        self.data: Dict[str, Any] = copy.deepcopy(DEFAULTS)
        self.load()

    # -- persistence -------------------------------------------------------
    def load(self) -> None:
        with self._lock:
            if os.path.exists(self.path):
                try:
                    with open(self.path, encoding="utf-8") as fh:
                        disk = json.load(fh)
                    self.data = _deep_merge(copy.deepcopy(DEFAULTS), disk)
                except Exception:
                    # corrupt file -> keep a backup, fall back to defaults
                    try:
                        os.replace(self.path, self.path + ".bak")
                    except OSError:
                        pass
                    self.data = copy.deepcopy(DEFAULTS)
            if not self.data.get("clocks"):
                self.data["clocks"] = [self.new_clock("Main Clock")]
            # make sure every clock has every key (forward compatibility)
            for i, c in enumerate(self.data["clocks"]):
                merged = default_clock()
                merged.update(c)
                if not merged.get("id"):
                    merged["id"] = f"clock-{i + 1}"
                # Sanity-clamp geometry: a corrupt or hand-edited file must
                # never produce a 30000 px window or a clock stuck off-screen.
                try:
                    merged["width"] = int(max(80, min(int(merged.get("width", 420)), 8000)))
                    merged["height"] = int(max(50, min(int(merged.get("height", 180)), 8000)))
                    merged["x"] = int(max(-10000, min(int(merged.get("x", 80)), 20000)))
                    merged["y"] = int(max(-10000, min(int(merged.get("y", 80)), 20000)))
                    merged["opacity"] = max(0.15, min(float(merged.get("opacity", 0.92)), 1.0))
                    merged["scale"] = max(0.15, min(float(merged.get("scale", 1.0)), 5.0))
                except (TypeError, ValueError):
                    pass
                if merged.get("face") not in _KNOWN_FACES:
                    merged["face"] = "digital"
                # migrate pre-1.3 files that only had always_on_top
                if "z_mode" not in c:
                    merged["z_mode"] = "top" if c.get("always_on_top", True) else "normal"
                self.data["clocks"][i] = merged

    def save(self) -> None:
        with self._lock:
            tmp = self.path + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(self.data, fh, indent=2, ensure_ascii=False)
                os.replace(tmp, self.path)
            except OSError:
                pass

    # -- helpers -----------------------------------------------------------
    def new_clock(self, name: str = "Clock") -> Dict[str, Any]:
        existing = {c.get("id") for c in self.data.get("clocks", [])}
        n = 1
        while f"clock-{n}" in existing:
            n += 1
        c = default_clock(name)
        c["id"] = f"clock-{n}"
        return c

    @property
    def clocks(self) -> List[Dict[str, Any]]:
        return self.data["clocks"]

    @property
    def general(self) -> Dict[str, Any]:
        return self.data["general"]

    @property
    def timesync(self) -> Dict[str, Any]:
        return self.data["timesync"]

    @property
    def alerts(self) -> Dict[str, Any]:
        return self.data["alerts"]

    @property
    def sessions_cfg(self) -> Dict[str, Any]:
        return self.data["sessions"]

    @property
    def alarms(self) -> List[Dict[str, Any]]:
        return self.data.setdefault("alarms", [])

    def new_alarm_id(self) -> str:
        existing = {a.get("id") for a in self.alarms}
        n = 1
        while f"alarm-{n}" in existing:
            n += 1
        return f"alarm-{n}"

    def clock_by_id(self, cid: str):
        for c in self.clocks:
            if c["id"] == cid:
                return c
        return None


def _deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_merge(base[k], v)
        else:
            base[k] = v
    return base
