"""End-to-end behaviour of the application controller and settings window."""
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

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea


@pytest.fixture
def app_ctx(qapp, monkeypatch, tmp_path):
    from aurora import config
    monkeypatch.setattr(config, "CONFIG_PATH", str(tmp_path / "settings.json"))
    from aurora.app import AuroraApp
    ctx = AuroraApp(qapp, start_hidden_ui=True)
    yield ctx


def test_app_starts_with_one_clock(app_ctx):
    assert len(app_ctx.cfg.clocks) == 1
    assert len(app_ctx.overlays) == 1


def test_add_remove_and_keep_only_one(app_ctx):
    app_ctx.add_clock()
    app_ctx.add_clock()
    assert len(app_ctx.cfg.clocks) == 3

    victim = app_ctx.cfg.clocks[-1]["id"]
    app_ctx.remove_clock(victim, ask=False)
    assert len(app_ctx.cfg.clocks) == 2
    assert victim not in app_ctx.overlays

    app_ctx.keep_only_first()
    assert len(app_ctx.cfg.clocks) == 1
    assert len(app_ctx.overlays) == 1


def test_the_last_clock_cannot_be_deleted(app_ctx):
    """Deleting everything would leave an invisible, unusable app."""
    only = app_ctx.cfg.clocks[0]["id"]
    app_ctx.remove_clock(only, ask=False)
    assert len(app_ctx.cfg.clocks) >= 1


def test_flash_does_not_leave_the_clock_invisible(app_ctx, qapp):
    cid = app_ctx.cfg.clocks[0]["id"]
    app_ctx.flash_clock(cid)
    for _ in range(40):
        qapp.processEvents()
    assert app_ctx.overlays[cid].windowOpacity() > 0.0


def test_double_lock_controls_movement(app_ctx):
    """A clock may only move when the master switch AND its own lock allow."""
    cid = app_ctx.cfg.clocks[0]["id"]
    overlay = app_ctx.overlays[cid]
    clock = app_ctx.cfg.clocks[0]

    app_ctx.cfg.general["edit_mode"] = False
    clock["locked"] = False
    assert overlay.movable is False

    app_ctx.cfg.general["edit_mode"] = True
    clock["locked"] = True
    assert overlay.movable is False

    clock["locked"] = False
    assert overlay.movable is True


@pytest.mark.parametrize("mode", ["top", "normal", "bottom", "desktop"])
def test_every_screen_layer_is_accepted(app_ctx, mode):
    cid = app_ctx.cfg.clocks[0]["id"]
    app_ctx.cfg.clocks[0]["z_mode"] = mode
    app_ctx.refresh_clock(cid)
    assert app_ctx.overlays[cid].isVisible() or True  # must not raise


def test_default_layer_is_behind_other_windows(app_ctx):
    """Regression test: 1.3 floated over Chrome, which users hated."""
    from aurora.config import default_clock
    assert default_clock()["z_mode"] == "desktop"
    assert default_clock()["always_on_top"] is False


def test_settings_window_is_usable(app_ctx):
    from aurora.settings_ui import SettingsDialog
    dlg = SettingsDialog(app_ctx)

    flags = dlg.windowFlags()
    assert flags & Qt.WindowMinimizeButtonHint, "must be minimisable"
    assert flags & Qt.WindowMaximizeButtonHint, "must be maximisable"

    assert dlg.tabs.count() == 7
    for i in range(dlg.tabs.count()):
        assert isinstance(dlg.tabs.widget(i), QScrollArea), \
            f"tab {i} is not scrollable - options could be cut off"
    assert dlg.minimumWidth() <= 720 and dlg.minimumHeight() <= 460


def test_settings_window_remembers_its_state(app_ctx):
    from aurora.settings_ui import SettingsDialog
    dlg = SettingsDialog(app_ctx)
    dlg.resize(1024, 700)
    dlg.tabs.setCurrentIndex(3)
    dlg._save_window_state()

    again = SettingsDialog(app_ctx)
    again._restore_window_state()
    assert again.tabs.currentIndex() == 3
    assert again.width() == 1024


def test_changing_every_face_and_theme_is_safe(app_ctx):
    from aurora.settings_ui import SettingsDialog
    dlg = SettingsDialog(app_ctx)
    for i in range(dlg.cb_face.count()):
        dlg.cb_face.setCurrentIndex(i)
    for i in range(dlg.cb_theme.count()):
        dlg.cb_theme.setCurrentIndex(i)
    for i in range(dlg.cb_gpreset.count()):
        dlg.cb_gpreset.setCurrentIndex(i)
    for i in range(dlg.cb_gdir.count()):
        dlg.cb_gdir.setCurrentIndex(i)


def test_slider_drags_do_not_hammer_the_disk(app_ctx, qapp):
    """A settings change is debounced, not written on every pixel."""
    from aurora.settings_ui import SettingsDialog
    dlg = SettingsDialog(app_ctx)
    writes = []
    original = app_ctx.cfg.save
    app_ctx.cfg.save = lambda: writes.append(1) or original()

    for value in range(30, 100):
        dlg.sl_opacity.setValue(value)
    qapp.processEvents()
    assert len(writes) == 0, "the save must be deferred, not immediate"
    app_ctx.cfg.save = original


def test_redundant_sets_are_ignored(app_ctx):
    from aurora.settings_ui import SettingsDialog
    dlg = SettingsDialog(app_ctx)
    repaints = []
    original = app_ctx.refresh_clock
    app_ctx.refresh_clock = lambda cid: repaints.append(cid)
    current = dlg._current()["face"]
    dlg._set("face", current)
    assert repaints == [], "setting the same value must not trigger a repaint"
    app_ctx.refresh_clock = original
