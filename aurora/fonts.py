"""Aurora Clock - font management.

Lets the user pick any installed font *and* load their own .ttf/.otf files,
which are registered with Qt at start-up so they survive restarts.
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
import shutil
from typing import Dict, List

from PySide6.QtGui import QFontDatabase

from .config import config_dir

# Fonts that look particularly good on a clock, offered at the top of the list.
RECOMMENDED = [
    "Segoe UI", "Segoe UI Light", "Segoe UI Semibold", "Segoe UI Variable Display",
    "Bahnschrift", "Bahnschrift Light", "Bahnschrift SemiBold",
    "Consolas", "Cascadia Code", "Cascadia Mono", "Lucida Console",
    "Calibri", "Candara", "Corbel", "Franklin Gothic Medium", "Tahoma", "Verdana",
    "Arial", "Arial Narrow", "Trebuchet MS", "Century Gothic",
    "Georgia", "Times New Roman", "Palatino Linotype", "Garamond",
    "Impact", "Agency FB", "Rockwell", "Courier New",
    # Bengali / Unicode friendly
    "Nirmala UI", "Shonar Bangla", "Vrinda", "Noto Sans", "Noto Sans Bengali",
]

FONTS_DIR = os.path.join(config_dir(), "fonts")

_loaded: Dict[str, List[str]] = {}


def installed_families() -> List[str]:
    return sorted(set(QFontDatabase.families()))


def ordered_families() -> List[tuple[str, str]]:
    """[(family, group)] with the recommended ones first."""
    have = set(installed_families())
    out: List[tuple[str, str]] = []
    for f in RECOMMENDED:
        if f in have:
            out.append((f, "Recommended"))
    rec = {f for f, _ in out}
    for f in installed_families():
        if f not in rec:
            out.append((f, "All fonts"))
    return out


def load_custom_file(path: str) -> List[str]:
    """Register a font file with Qt; returns the families it provides."""
    if not os.path.isfile(path):
        return []
    fid = QFontDatabase.addApplicationFont(path)
    if fid < 0:
        return []
    fams = QFontDatabase.applicationFontFamilies(fid)
    _loaded[path] = list(fams)
    return list(fams)


def import_font(path: str, cfg) -> List[str]:
    """Copy a font next to the settings file so it keeps working after a move."""
    os.makedirs(FONTS_DIR, exist_ok=True)
    dest = os.path.join(FONTS_DIR, os.path.basename(path))
    try:
        if os.path.abspath(path) != os.path.abspath(dest):
            shutil.copy2(path, dest)
    except OSError:
        dest = path
    fams = load_custom_file(dest)
    if fams:
        files = cfg.data.setdefault("fonts", {}).setdefault("custom_files", [])
        if dest not in files:
            files.append(dest)
            cfg.save()
    return fams


def load_all(cfg) -> List[str]:
    """Called once at start-up."""
    fams: List[str] = []
    for path in list(cfg.data.get("fonts", {}).get("custom_files", [])):
        fams += load_custom_file(path)
    if os.path.isdir(FONTS_DIR):
        for name in os.listdir(FONTS_DIR):
            if name.lower().endswith((".ttf", ".otf", ".ttc")):
                full = os.path.join(FONTS_DIR, name)
                if full not in _loaded:
                    fams += load_custom_file(full)
    return fams


def custom_families() -> List[str]:
    out: List[str] = []
    for fams in _loaded.values():
        out += fams
    return sorted(set(out))
