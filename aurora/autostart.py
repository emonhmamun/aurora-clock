"""Aurora Clock - run at Windows login.

Uses the per-user Run key in HKCU, which needs no administrator rights and is
the officially supported way for a user-level utility to start with Windows.
A Linux/macOS fallback is included so the code can be developed anywhere.
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

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "AuroraClock"


def launch_command() -> str:
    """Command line that re-launches this app, quoted for the registry."""
    exe = sys.executable
    if getattr(sys, "frozen", False):           # PyInstaller build
        return f'"{exe}" --tray'
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    pyw = exe.replace("python.exe", "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    return f'"{exe}" "{script}" --tray'


# ---------------------------------------------------------------- windows ---
def _win_set(enabled: bool) -> bool:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, launch_command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def _win_get() -> bool:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
        return True
    except OSError:
        return False


# ------------------------------------------------------------------ linux ---
_DESKTOP_PATH = os.path.expanduser("~/.config/autostart/aurora-clock.desktop")


def _nix_set(enabled: bool) -> bool:
    try:
        if enabled:
            os.makedirs(os.path.dirname(_DESKTOP_PATH), exist_ok=True)
            cmd = launch_command().replace('"', "")
            with open(_DESKTOP_PATH, "w", encoding="utf-8") as fh:
                fh.write(
                    "[Desktop Entry]\nType=Application\nName=Aurora Clock\n"
                    f"Exec={cmd}\nX-GNOME-Autostart-enabled=true\nTerminal=false\n"
                )
        elif os.path.exists(_DESKTOP_PATH):
            os.remove(_DESKTOP_PATH)
        return True
    except OSError:
        return False


def _nix_get() -> bool:
    return os.path.exists(_DESKTOP_PATH)


# ------------------------------------------------------------------- api ----
def set_autostart(enabled: bool) -> bool:
    return _win_set(enabled) if sys.platform == "win32" else _nix_set(enabled)


def is_autostart() -> bool:
    try:
        return _win_get() if sys.platform == "win32" else _nix_get()
    except Exception:
        return False
