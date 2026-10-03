"""Shared pytest fixtures.

Every test runs Qt on the ``offscreen`` platform plugin and redirects the
settings directory into a temporary folder, so running the suite can never
touch a real user's configuration.
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
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Point the config directory somewhere disposable *before* aurora.config is
# imported anywhere: it resolves %APPDATA% / $XDG_CONFIG_HOME at import time.
_TMP = tempfile.mkdtemp(prefix="aurora-tests-")
os.environ["APPDATA"] = _TMP
os.environ["XDG_CONFIG_HOME"] = _TMP


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def cfg(tmp_path):
    from aurora.config import Config
    c = Config(str(tmp_path / "settings.json"))
    c.load()
    return c
