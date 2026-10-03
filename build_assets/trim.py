"""Remove the parts of the Qt runtime Aurora Clock never touches.

Run after PyInstaller, before building the installer.  Everything deleted
here is verified unused: Aurora draws with the raster engine only, never
loads QML/Quick, never opens a network socket through Qt and ships no
translations.
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
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "AuroraClock", "_internal")

# whole directories that are never used
DROP_DIRS = [
    "PySide6/translations",
    "PySide6/plugins/iconengines",
    "PySide6/plugins/generic",
    "PySide6/plugins/networkinformation",
    "PySide6/plugins/tls",
    "PySide6/plugins/sqldrivers",
    "PySide6/plugins/qmltooling",
    "PySide6/plugins/multimedia",
    "PySide6/plugins/canbus",
    "PySide6/plugins/designer",
    "PySide6/qml",
    "PySide6/typesystems",
    "PySide6/glue",
    "PySide6/include",
]

# individual files
DROP_FILES = [
    "PySide6/opengl32sw.dll",        # ~20 MB software OpenGL rasteriser
    "PySide6/d3dcompiler_47.dll",    # ~4 MB, only needed by Qt Quick
    "PySide6/Qt6Network.dll",
    "PySide6/Qt6Svg.dll",
    "PySide6/Qt6Qml.dll",
    "PySide6/Qt6QmlModels.dll",
    "PySide6/Qt6Quick.dll",
    "PySide6/Qt6OpenGL.dll",
    "PySide6/Qt6Pdf.dll",
    "PySide6/Qt6VirtualKeyboard.dll",
    "PySide6/QtNetwork.pyd",
    "PySide6/QtSvg.pyd",
]

# image formats we actually need (wallpaper reading + the icon)
KEEP_IMAGEFORMATS = {"qjpeg", "qico", "qgif", "qwebp"}


def human(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB"


def tree_size(path: str) -> int:
    total = 0
    for base, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(base, f))
            except OSError:
                pass
    return total


def main() -> int:
    if not os.path.isdir(ROOT):
        print("nothing to trim at", ROOT)
        return 1
    before = tree_size(os.path.dirname(ROOT))
    freed = 0

    for rel in DROP_DIRS:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if os.path.isdir(p):
            freed += tree_size(p)
            shutil.rmtree(p, ignore_errors=True)

    for rel in DROP_FILES:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if os.path.isfile(p):
            freed += os.path.getsize(p)
            os.remove(p)

    imgdir = os.path.join(ROOT, "PySide6", "plugins", "imageformats")
    if os.path.isdir(imgdir):
        for name in os.listdir(imgdir):
            stem = os.path.splitext(name)[0]
            if stem not in KEEP_IMAGEFORMATS:
                p = os.path.join(imgdir, name)
                try:
                    freed += os.path.getsize(p)
                    os.remove(p)
                except OSError:
                    pass

    # keep only the Windows platform plugin
    platdir = os.path.join(ROOT, "PySide6", "plugins", "platforms")
    if os.path.isdir(platdir):
        for name in os.listdir(platdir):
            if "windows" not in name.lower():
                p = os.path.join(platdir, name)
                try:
                    freed += os.path.getsize(p)
                    os.remove(p)
                except OSError:
                    pass

    after = tree_size(os.path.dirname(ROOT))
    print(f"trimmed {human(freed)}   {human(before)} -> {human(after)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
