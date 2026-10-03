"""Aurora Clock — a lightweight always-on-top desktop clock overlay for Windows.

Usage:
    AuroraClock.exe              start normally
    AuroraClock.exe --tray       start silently into the tray (used by autostart)
    AuroraClock.exe --settings   start and open the settings window
    AuroraClock.exe --reset      start from factory settings (keeps a backup)
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

MUTEX_NAME = "Global\\AuroraClock.SingleInstance.v1"


def _already_running() -> bool:
    """Reliable single-instance check.

    A named kernel mutex is the way Windows applications do this: it is
    released automatically when the process dies, so a crash can never leave
    a stale lock behind (which is exactly how duplicate clocks appear).
    """
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL,
                                              wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
            err = ctypes.get_last_error()
            # keep a reference so the handle lives as long as the process
            globals()["_mutex_handle"] = handle
            return err == 183  # ERROR_ALREADY_EXISTS
        except Exception:
            return False

    # POSIX fallback: an exclusive lock on a file in the config directory
    try:
        import fcntl

        from aurora.config import config_dir
        path = os.path.join(config_dir(), "instance.lock")
        fh = open(path, "w")  # noqa: SIM115 - must stay open for the process lifetime
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        globals()["_lock_file"] = fh
        return False
    except Exception:
        return True


def main() -> int:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QMessageBox

    args = {a.lower() for a in sys.argv[1:]}

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    # we never use OpenGL; this keeps start-up fast and memory small
    QApplication.setAttribute(Qt.AA_DisableShaderDiskCache, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Aurora Clock")
    app.setOrganizationName("Aurora")
    app.setQuitOnLastWindowClosed(False)   # keep living in the tray

    if _already_running():
        if "--tray" not in args:
            QMessageBox.information(
                None, "Aurora Clock",
                "Aurora Clock is already running.\n\n"
                "Look for its icon in the system tray (next to the Windows "
                "clock, under the ^ arrow). Right-click it for settings.")
        return 0

    from aurora.config import Config

    if "--reset" in args:
        cfg_path = Config().path
        if os.path.exists(cfg_path):
            try:
                os.replace(cfg_path, cfg_path + ".backup")
            except OSError:
                pass

    from aurora.app import AuroraApp

    probe = Config()
    first_run = probe.data.get("first_run", True)
    hidden = ("--tray" in args) or (probe.general.get("start_minimised", True)
                                    and not first_run and "--settings" not in args)
    if "--settings" in args:
        hidden = False

    aurora = AuroraApp(app, start_hidden_ui=hidden)
    _ = aurora  # keep a reference alive
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
