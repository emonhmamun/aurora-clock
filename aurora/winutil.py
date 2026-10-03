"""Aurora Clock - native Windows window management.

This is the module that makes the overlay behave like a real desktop widget:

* it keeps the requested Z order (always-on-top / normal / behind every window
  / glued onto the wallpaper) even after Explorer restarts or the desktop is
  refreshed, which is what makes naive overlays disappear;
* it keeps the window out of the taskbar and out of Alt-Tab;
* it stops the window from ever stealing focus (WS_EX_NOACTIVATE);
* it survives "Show desktop" (Win+D), screen-resolution changes, RDP
  reconnects and user switching.

Every function degrades to a harmless no-op on non-Windows systems so the
code can still be developed and tested on Linux.
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
from typing import List, Optional

IS_WIN = sys.platform == "win32"

# --- Z-order modes ---------------------------------------------------------
Z_TOP = "top"          # above everything, always visible
Z_NORMAL = "normal"    # behaves like an ordinary window
Z_BOTTOM = "bottom"    # below every other window; visible on an empty desktop
Z_DESKTOP = "desktop"  # glued to the wallpaper itself (survives Show Desktop)

Z_LABELS = {
    Z_TOP:     "Always on top — above every program",
    Z_NORMAL:  "Normal — behaves like a regular window",
    Z_BOTTOM:  "Background — below every program (visible on the empty desktop)",
    Z_DESKTOP: "On the wallpaper — behind icons, survives “Show desktop”",
}

if IS_WIN:  # pragma: no cover - Windows only
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    HWND_TOP = 0
    HWND_BOTTOM = 1
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2

    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040
    SWP_NOOWNERZORDER = 0x0200
    SWP_NOSENDCHANGING = 0x0400

    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_NOACTIVATE = 0x08000000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_APPWINDOW = 0x00040000
    WS_EX_LAYERED = 0x00080000

    SW_SHOWNOACTIVATE = 4

    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_uint]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_longlong
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_longlong]
    user32.SetWindowLongPtrW.restype = ctypes.c_longlong
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND,
                                     wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowExW.restype = wintypes.HWND
    user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterWindowMessageW.restype = ctypes.c_uint
else:
    user32 = None  # type: ignore


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def hwnd_of(widget) -> int:
    try:
        return int(widget.winId())
    except Exception:
        return 0


def _ex_style(hwnd: int, add: int = 0, remove: int = 0) -> None:
    if not IS_WIN or not hwnd:
        return
    try:
        cur = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        new = (cur | add) & ~remove
        if new != cur:
            user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new)
    except Exception:
        pass


def prepare_window(hwnd: int, click_through: bool = False) -> None:
    """Apply the extended styles an overlay should always have."""
    if not IS_WIN or not hwnd:
        return
    add = WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    remove = WS_EX_APPWINDOW
    if click_through:
        add |= WS_EX_TRANSPARENT
    else:
        remove |= WS_EX_TRANSPARENT
    _ex_style(hwnd, add, remove)


# ---------------------------------------------------------------------------
# wallpaper (WorkerW) attachment
# ---------------------------------------------------------------------------

def _find_workerw() -> int:
    """The WorkerW window that sits between the wallpaper and the icons."""
    if not IS_WIN:
        return 0
    try:
        progman = user32.FindWindowW("Progman", None)
        if progman:
            # ask Progman to spawn the WorkerW layer (ignore the result)
            result = ctypes.c_ulonglong()
            user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0x0000, 1000,
                                       ctypes.byref(result))
        found: List[int] = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def _cb(hwnd, _lparam):
            shell_view = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
            if shell_view:
                worker = user32.FindWindowExW(None, hwnd, "WorkerW", None)
                if worker:
                    found.append(worker)
            return True

        user32.EnumWindows(WNDENUMPROC(_cb), 0)
        if found:
            return found[0]
        # some builds keep the layer directly under Progman
        return user32.FindWindowExW(progman, None, "WorkerW", None) or 0
    except Exception:
        return 0


def attach_to_wallpaper(hwnd: int) -> bool:
    if not IS_WIN or not hwnd:
        return False
    worker = _find_workerw()
    if not worker:
        return False
    try:
        user32.SetParent(hwnd, worker)
        return True
    except Exception:
        return False


def detach_from_wallpaper(hwnd: int) -> None:
    if not IS_WIN or not hwnd:
        return
    try:
        user32.SetParent(hwnd, None)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Z order
# ---------------------------------------------------------------------------

def is_at_bottom(hwnd: int) -> bool:
    """True when no other visible top-level window sits below us."""
    if not IS_WIN or not hwnd:
        return True
    try:
        GW_HWNDNEXT = 2
        nxt = user32.GetWindow(hwnd, GW_HWNDNEXT)
        while nxt:
            if user32.IsWindowVisible(nxt):
                cls = ctypes.create_unicode_buffer(64)
                user32.GetClassNameW(nxt, cls, 64)
                # the wallpaper layers are legitimately below us
                if cls.value not in ("WorkerW", "Progman", "SysShadow"):
                    return False
            nxt = user32.GetWindow(nxt, GW_HWNDNEXT)
        return True
    except Exception:
        return True


def is_topmost(hwnd: int) -> bool:
    if not IS_WIN or not hwnd:
        return False
    try:
        return bool(user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE) & 0x00000008)  # WS_EX_TOPMOST
    except Exception:
        return False


def apply_z_order(hwnd: int, mode: str, show: bool = True, force: bool = False) -> None:
    """(Re-)assert the window's position in the Z order.

    The checks keep this almost free when nothing has changed, which matters
    because the watchdog calls it for every clock a few times a minute.
    """
    if not IS_WIN or not hwnd:
        return
    flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOOWNERZORDER | SWP_NOSENDCHANGING
    if show and force:
        flags |= SWP_SHOWWINDOW
    try:
        if mode == Z_TOP:
            if force or not is_topmost(hwnd):
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
        elif mode in (Z_BOTTOM, Z_DESKTOP):
            if is_topmost(hwnd):
                user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
            if force or not is_at_bottom(hwnd):
                user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, flags)
        else:
            if is_topmost(hwnd):
                user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
    except Exception:
        pass


def ensure_visible(hwnd: int) -> None:
    """Show the window without giving it focus."""
    if not IS_WIN or not hwnd:
        return
    try:
        if not user32.IsWindowVisible(hwnd):
            user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# shell restart detection
# ---------------------------------------------------------------------------

def taskbar_created_message() -> int:
    """Broadcast message Explorer sends after it restarts."""
    if not IS_WIN:
        return 0
    try:
        return int(user32.RegisterWindowMessageW("TaskbarCreated"))
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# foreground window inspection (for the full-screen auto-hide)
# ---------------------------------------------------------------------------

def foreground_is_fullscreen(own_hwnds: Optional[List[int]] = None) -> bool:
    if not IS_WIN:
        return False
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        if own_hwnds and hwnd in own_hwnds:
            return False
        shell = user32.GetShellWindow()
        desktop = user32.GetDesktopWindow()
        if hwnd in (shell, desktop):
            return False
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value in ("WorkerW", "Progman", "Shell_TrayWnd"):
            return False
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        mi_w = user32.GetSystemMetrics(0)   # SM_CXSCREEN
        mi_h = user32.GetSystemMetrics(1)   # SM_CYSCREEN
        return (rect.right - rect.left) >= mi_w and (rect.bottom - rect.top) >= mi_h
    except Exception:
        return False
