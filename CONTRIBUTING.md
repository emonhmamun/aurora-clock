# Contributing to Aurora Clock

Thank you for considering a contribution. Aurora Clock is a small, focused
project with one guiding rule:

> **It must stay light, and it must never get in the user's way.**

Anything that makes the clock heavier, slower, chattier or more intrusive will
be pushed back on — not because the idea is bad, but because "a clock" is the
entire product.

---

## Table of contents

- [Ways to help](#ways-to-help)
- [Setting up](#setting-up)
- [Project layout](#project-layout)
- [Running the tests](#running-the-tests)
- [Coding style](#coding-style)
- [Writing a new clock face](#writing-a-new-clock-face)
- [Adding a theme](#adding-a-theme)
- [Performance rules](#performance-rules)
- [Security rules](#security-rules)
- [Commit and pull request conventions](#commit-and-pull-request-conventions)
- [Releasing](#releasing)
- [Licence of contributions](#licence-of-contributions)

---

## Ways to help

| | |
|---|---|
| 🎨 **New clock faces** | The most welcome contribution. See the [guide below](#writing-a-new-clock-face). |
| 🌈 **Themes & gradients** | A one-line dictionary entry — a great first PR. |
| 🌍 **Trading sessions** | Add your local exchange to `aurora/sessions.py`. |
| 🐛 **Bug reports** | Please use the [bug template](../../issues/new/choose) and include your `settings.json` with any personal labels removed. |
| 📖 **Documentation** | Typos, clearer wording and screenshots all count. |
| 🧪 **Tests** | Especially regression tests for bugs you hit yourself. |

---

## Setting up

```bash
git clone https://github.com/emonhmamun/aurora-clock.git
cd aurora-clock

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements-dev.txt
python main.py
```

**You do not need Windows to develop Aurora Clock.** The faces, themes, config
layer and settings window all run on Linux and macOS. The Windows-only parts
(`winutil.py`, `autostart.py`) degrade to no-ops, so you can work on rendering
and UI anywhere. Please state in your PR which platform you tested on.

On a headless Linux box, run Qt offscreen:

```bash
export QT_QPA_PLATFORM=offscreen
```

---

## Project layout

```
aurora-clock/
├── main.py                  entry point, CLI flags, single-instance mutex
├── aurora/
│   ├── app.py               AuroraApp: tray icon, clock manager, watchdog
│   ├── overlay.py           ClockOverlay: the frameless window + render loop
│   ├── faces.py             all 20 clock faces + the drawing/FX pipeline
│   ├── themes.py            the 28 colour palettes
│   ├── settings_ui.py       the settings window
│   ├── config.py            defaults, load/save, validation, migration
│   ├── winutil.py           native Win32 Z-order and window helpers
│   ├── autostart.py         HKCU Run key management
│   ├── timesync.py          NTP client
│   ├── sessions.py          trading-session catalogue and status engine
│   ├── alerts.py            alarms, chimes, session transition alerts
│   ├── timezones.py         IANA zone helpers
│   ├── contrast.py          wallpaper sampling for automatic light/dark text
│   ├── fonts.py             system and user font management
│   └── banner.py            transient on-screen notifications
├── build_assets/            PyInstaller spec, Inno Setup script, icon, trim.py
├── docs/                    the documentation you are reading
└── tests/                   pytest suite (~200 tests)
```

### Design invariants

These are load-bearing. Please do not break them without discussing it first.

1. **A face is a pure function.** `render(painter, rect, ctx) -> None`. It must
   not read global state, start timers, touch the filesystem or the network.
2. **Everything is laid out relative to `rect`.** No hard-coded pixel sizes —
   a face must look right at 220 × 90 and at 1200 × 400.
3. **All drawing goes through `draw_path_fx` / `draw_shape_fx`.** That is how
   every face automatically gets shadow, outline, glow, contrast plate and
   gradient support for free.
4. **The system clock is never modified.** Time corrections are applied when
   rendering.
5. **Z-order lives in the native layer**, not in Qt window flags. Qt has no
   "always at the bottom" hint.
6. **A clock moves only when `not locked AND general.edit_mode AND not
   click_through`.**

---

## Running the tests

```bash
pytest -q                       # the whole suite, a few seconds
pytest tests/test_faces.py -q   # just the renderer
pytest -q -k gradient           # anything matching "gradient"
```

Also run the linter before opening a PR:

```bash
ruff check .
python -m pyflakes main.py aurora/*.py
```

CI runs the same commands on Windows and Linux. **A PR that fails CI will not
be merged.**

### Tests you must add

| If you change… | Add a test to… |
|---|---|
| a clock face | `tests/test_faces.py` (it is parametrised — a new face is picked up automatically, but add a specific test for unusual geometry) |
| settings defaults or migration | `tests/test_config.py` |
| the NTP client | `tests/test_timesync.py` |
| the settings window or app controller | `tests/test_app.py` |
| anything touching the network, registry, or process spawning | `tests/test_security.py` |

---

## Coding style

- **PEP 8**, 4-space indent, max line length **100**.
- `from __future__ import annotations` at the top of every module.
- Type hints on public functions. `-> None` is not optional.
- **British English** in user-facing strings (*colour*, *centre*, *minimise*),
  to match the existing UI.
- Docstrings explain **why**, not what. The code already says what.
- No new third-party runtime dependencies without discussion. PySide6 and the
  standard library should be enough.
- Keep comments honest — if something is a workaround for a Windows quirk, say
  so and name the quirk.

---

## Writing a new clock face

A face is one function. Here is a complete, working example:

```python
def face_example(p: QPainter, r: QRectF, ctx: FaceContext) -> None:
    """One sentence describing what the user sees."""
    hh, mm, ss, ap = _time_parts(ctx)

    text = f"{hh}:{mm}"
    if ctx.show_seconds:
        text += f":{ss}"

    # Lay everything out relative to `r` so the face scales to any window.
    font = ctx.font(r.height() * 0.7)
    _fit_text(p, r, text, font, ctx.color("fg"), Qt.AlignCenter)
```

Then register it in **three** places in `aurora/faces.py`:

```python
FACES = {..., "example": face_example}
FACE_LABELS = {..., "example": "Example face"}
# optional:
SQUARE_FACES = {..., "example"}   # if it needs a square window
SESSION_FACES = {..., "example"}  # if it uses ctx.sessions
```

…and add the key to `_KNOWN_FACES` in `aurora/config.py` (a test enforces that
the two stay in sync).

### What `ctx` gives you

| Attribute | Meaning |
|---|---|
| `ctx.now` | `datetime` already converted to the clock's time zone and NTP-corrected |
| `ctx.sub_second` | 0.0–1.0 within the current second, for smooth animation |
| `ctx.now_utc` | corrected UTC, for session faces |
| `ctx.sessions` | pre-computed `SessionStatus` list (never compute these yourself) |
| `ctx.pal` | the resolved palette dict |
| `ctx.settings` | the clock's settings dict |
| `ctx.label` | the clock's label (city name by default) |
| `ctx.quality` | `"low" \| "balanced" \| "smooth"` |
| `ctx.color(key, alpha=1.0)` | a `QColor` from the palette |
| `ctx.font(size, weight=None, mono=False)` | a `QFont` honouring the user's font choice |
| `ctx.hour24`, `ctx.show_seconds`, `ctx.smooth` | convenience flags |

### Helpers you should use

| Helper | Purpose |
|---|---|
| `_fit_text(p, rect, text, font, color, align)` | shrink-to-fit text through the FX pipeline |
| `_draw_glow_text(...)` | big headline text |
| `_text_path(rect, text, font, align)` | get the `QPainterPath` yourself |
| `draw_path_fx(p, path, color)` | fill a path with shadow/outline/glow/gradient |
| `draw_shape_fx(p, path, pen)` | the same for stroked shapes (analog hands) |
| `_time_parts(ctx)` | `(hh, mm, ss, am/pm)` respecting 12/24-hour |
| `_date_text(ctx)` | the formatted date string |

### Checklist before you open the PR

- [ ] It renders at 220 × 90, 640 × 280, 300 × 300 and 1200 × 160.
- [ ] It respects `show_date`, `show_label`, `show_ampm`, `hour24` and
      `seconds_mode` (including `hidden`).
- [ ] It looks right in a light theme (*Paper*, *Ink*, *Sand*) as well as dark.
- [ ] Gradients work (`pytest -k gradient` covers this automatically).
- [ ] It draws nothing outside `r`.
- [ ] `pytest -q` passes.
- [ ] A screenshot is attached to the PR.

---

## Adding a theme

One entry in `THEMES` and one in `THEME_LABELS` in `aurora/themes.py`:

```python
"my_theme": {"fg": "#EAF6FF", "accent": "#38E1C6", "dim": "#8FA6B8",
             "bg": "#0D1724", "glow": "#38E1C6"},
```

| Key | Used for |
|---|---|
| `fg` | primary text and analog hands |
| `accent` | seconds hand, AM/PM, highlights |
| `dim` | date, labels, secondary text |
| `bg` | panel background when a backdrop is enabled |
| `glow` | the halo colour |

All five keys are required, all must be `#RRGGBB` (a test checks this), and the
theme must be readable on both a dark and a light wallpaper — check it against
the *Colourful* and *Transparency* preview backdrops.

---

## Performance rules

Aurora Clock runs for twelve hours a day on someone's laptop battery. These are
not suggestions:

1. **Never reintroduce an unconditional repaint timer.** The overlay repaints
   only when `_content_key()` changes. A digital clock must cost ~1 repaint per
   second, not 25.
2. **Do not do work in `paintEvent` that could be cached.** Session statuses
   are cached for ≤ 1 s; reuse them via `ctx.sessions`.
3. **Respect `ctx.quality`.** Expensive effects must scale down on *Power saver*.
4. **No disk writes in a hot path.** Use the debounced save (`_save_soon()`).
5. **The watchdog must be a no-op when nothing has changed.** Never call
   `SetWindowPos` with `force=True` from a timer — it flickers and burns CPU.

If your change could affect the repaint rate, say so in the PR and include
before/after numbers.

---

## Security rules

See [SECURITY.md](SECURITY.md) for the full threat model. In short, a PR must
not introduce:

- `eval`, `exec`, `compile`, `__import__`, `subprocess`, `os.system`,
  `shell=True`
- `pickle`, `marshal`, `shelve`, `yaml.load`
- any HTTP client, telemetry, analytics or auto-updater
- writes to `HKEY_LOCAL_MACHINE` or anything requiring administrator rights
- any call that changes the system clock

`tests/test_security.py` enforces every item automatically.

---

## Commit and pull request conventions

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(faces): add the arc gauge face
fix(settings): make tabs scrollable so options are not cut off
perf(overlay): repaint only when the rendered text changes
docs(readme): document the gradient presets
test(timesync): cover spoofed NTP replies
chore(build): trim opengl32sw.dll from the bundle
```

**Pull requests**

- One logical change per PR. A new face and a settings refactor are two PRs.
- Fill in the PR template.
- Include a screenshot for anything visual.
- Note the platform you tested on.
- Keep `CHANGELOG.md` updated under an `## [Unreleased]` heading.

---

## Releasing

Maintainers only.

1. Update `APP_VERSION` in `aurora/config.py`.
2. Update `build_assets/version_info.txt` and `build_assets/AuroraClock.iss`.
   *(`tests/test_security.py::test_version_strings_are_consistent` checks all
   three agree with the changelog.)*
3. Move `## [Unreleased]` to `## [x.y.z] — YYYY-MM-DD` in `CHANGELOG.md`.
4. `pytest -q` and `ruff check .` must be green.
5. Tag and push:
   ```bash
   git tag -a v1.5.0 -m "Aurora Clock 1.5.0"
   git push origin v1.5.0
   ```
6. The `release.yml` workflow builds the `.exe`, the portable zip and
   `checksums.txt` on a Windows runner and attaches them to a draft release.
7. Review the draft, paste the changelog section, and publish.

---

## Licence of contributions

Aurora Clock is licensed under the **GNU General Public License v3.0**.

By submitting a pull request you agree that your contribution is licensed under
GPL-3.0 as well, and that you have the right to submit it. There is no CLA and
no copyright assignment — you keep the copyright on your own work.
