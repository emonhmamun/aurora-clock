"""Every clock face must render, in every configuration, without raising."""
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

import itertools
from datetime import datetime, timezone

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter

from aurora import faces, themes

SIZES = [(640, 280), (220, 90), (300, 300), (1200, 160)]


def _ctx(**over):
    settings = {
        "face": "digital", "theme": "aurora", "font_family": "DejaVu Sans",
        "font_weight": 300, "show_date": True, "show_label": True,
        "show_ampm": True, "show_seconds": True, "seconds_mode": "smooth",
        "hour24": False, "blink_colon": False,
        "date_format": "dddd, d MMMM yyyy",
    }
    settings.update(over.pop("settings", {}))
    return faces.FaceContext(
        now=over.pop("now", datetime(2026, 10, 3, 18, 52, 57)),
        sub_second=over.pop("sub_second", 0.37),
        pal=themes.palette(settings.get("theme", "aurora")),
        settings=settings,
        label=over.pop("label", "DHAKA"),
        now_utc=datetime.now(timezone.utc),
        sessions=[],
        quality=over.pop("quality", "balanced"),
    )


def _render(ctx, w=640, h=280):
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    try:
        faces.render(p, QRectF(0, 0, w, h), ctx)
    finally:
        p.end()
    return img


@pytest.mark.parametrize("face", sorted(faces.FACES))
@pytest.mark.parametrize("size", SIZES)
def test_face_renders_at_every_size(qapp, face, size):
    _render(_ctx(settings={"face": face}), *size)


@pytest.mark.parametrize("face", sorted(faces.FACES))
def test_face_renders_with_gradient(qapp, face):
    _render(_ctx(settings={
        "face": face, "gradient_on": True, "gradient_preset": "sunset",
        "gradient_dir": "diagonal", "gradient_shapes": True,
    }))


@pytest.mark.parametrize("direction", sorted(faces.GRADIENT_DIRECTIONS))
def test_every_gradient_direction(qapp, direction):
    _render(_ctx(settings={
        "gradient_on": True, "gradient_dir": direction, "gradient_preset": "fire",
    }))


@pytest.mark.parametrize("preset", sorted(faces.GRADIENT_PRESETS))
def test_every_gradient_preset(qapp, preset):
    _render(_ctx(settings={"gradient_on": True, "gradient_preset": preset}))


@pytest.mark.parametrize("theme", sorted(themes.THEMES))
def test_every_theme_renders(qapp, theme):
    _render(_ctx(settings={"theme": theme}))


def test_registry_and_labels_agree():
    assert set(faces.FACES) == set(faces.FACE_LABELS)
    assert set(faces.FACES) >= faces.SESSION_FACES
    assert set(faces.FACES) >= faces.SQUARE_FACES


def test_every_theme_has_a_label_and_full_palette():
    for name, pal in themes.THEMES.items():
        assert name in themes.THEME_LABELS, f"{name} has no display label"
        assert {"fg", "accent", "dim", "bg", "glow"} <= set(pal)
        for key, value in pal.items():
            assert value.startswith("#") and len(value) == 7, f"{name}.{key}={value}"


@pytest.mark.parametrize("quality", ["low", "balanced", "smooth"])
def test_quality_levels(qapp, quality):
    _render(_ctx(quality=quality))


def test_extreme_option_combinations(qapp):
    """Nothing may blow up when the user turns everything on at once."""
    flags = ("show_date", "show_label", "show_ampm", "hour24", "blink_colon")
    for combo in itertools.product([True, False], repeat=len(flags)):
        _render(_ctx(settings=dict(zip(flags, combo), face="digital")))


def test_all_legibility_effects_together(qapp):
    _render(_ctx(settings={
        "fx_shadow": True, "fx_shadow_blur": 12.0, "fx_outline": 3.0,
        "fx_glow": 1.0, "fx_plate": True, "gradient_on": True,
    }))


def test_degenerate_rectangles_do_not_crash(qapp):
    for w, h in ((1, 1), (3, 200), (200, 3)):
        _render(_ctx(), w, h)


def test_midnight_and_noon(qapp):
    for when in (datetime(2026, 1, 1, 0, 0, 0), datetime(2026, 1, 1, 12, 0, 0)):
        for h24 in (True, False):
            _render(_ctx(now=when, settings={"hour24": h24}))


def test_date_tokenizer_does_not_rescan_output():
    ctx = _ctx(now=datetime(2026, 3, 7, 9, 5, 0))
    ctx.settings["date_format"] = "dddd, d MMMM yyyy"
    assert faces._date_text(ctx) == "Saturday, 7 March 2026"
    ctx.settings["date_format"] = "yyyy-MM-dd"
    assert faces._date_text(ctx) == "2026-03-07"
    ctx.settings["date_format"] = "ddd dd MMM yy"
    assert faces._date_text(ctx) == "Sat 07 Mar 26"
