"""Settings persistence, migration and hardening."""
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

import json
import os

from aurora import config


def test_defaults_are_complete(cfg):
    assert cfg.data["version"] == config.APP_VERSION
    assert cfg.clocks, "a fresh install must create one clock"
    c = cfg.clocks[0]
    for key in ("id", "name", "face", "theme", "x", "y", "width", "height",
                "locked", "opacity", "scale", "gradient_on", "gradient_preset"):
        assert key in c, f"missing default key: {key}"


def test_atomic_save_and_reload(cfg):
    cfg.clocks[0]["name"] = "Trading Desk"
    cfg.save()
    assert os.path.exists(cfg.path)
    assert not os.path.exists(cfg.path + ".tmp"), "temp file must be renamed away"

    other = config.Config(cfg.path)
    assert other.clocks[0]["name"] == "Trading Desk"


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = str(tmp_path / "settings.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{ this is not json ::::")
    c = config.Config(path)
    assert c.clocks, "a corrupt file must not stop the app from starting"
    assert os.path.exists(path + ".bak"), "the broken file must be kept as .bak"


def test_geometry_is_clamped(tmp_path):
    """A hand-edited or corrupt file must not create a monster window."""
    path = str(tmp_path / "settings.json")
    payload = {
        "clocks": [{
            "id": "clock-1", "name": "Bad", "width": 999999, "height": -40,
            "x": 10 ** 9, "y": -10 ** 9, "opacity": 42.0, "scale": 900.0,
            "face": "there-is-no-such-face",
        }]
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)

    c = config.Config(path)
    clock = c.clocks[0]
    assert 80 <= clock["width"] <= 8000
    assert 50 <= clock["height"] <= 8000
    assert -10000 <= clock["x"] <= 20000
    assert -10000 <= clock["y"] <= 20000
    assert 0.15 <= clock["opacity"] <= 1.0
    assert 0.15 <= clock["scale"] <= 5.0
    assert clock["face"] == "digital", "unknown faces must fall back safely"


def test_every_known_face_is_registered():
    """config._KNOWN_FACES must stay in step with faces.FACES."""
    from aurora import faces
    assert set(faces.FACES) == config._KNOWN_FACES


def test_new_clock_ids_are_unique(cfg):
    ids = {cfg.clocks[0]["id"]}
    for _ in range(25):
        c = cfg.new_clock("extra")
        assert c["id"] not in ids
        ids.add(c["id"])
        cfg.clocks.append(c)


def test_unicode_survives_a_roundtrip(cfg):
    cfg.clocks[0]["name"] = "ঢাকা ঘড়ি — 時計"
    cfg.save()
    reloaded = config.Config(cfg.path)
    assert reloaded.clocks[0]["name"] == "ঢাকা ঘড়ি — 時計"
