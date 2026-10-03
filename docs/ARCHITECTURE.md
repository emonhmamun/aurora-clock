# Architecture

How Aurora Clock is put together, and — more importantly — **why**. Most of the
non-obvious decisions here exist because Windows fought back.

---

## Overview

```
                     ┌──────────────────────────────────────┐
  main.py ──────────▶│  single-instance mutex, CLI flags    │
                     └───────────────┬──────────────────────┘
                                     ▼
                     ┌──────────────────────────────────────┐
                     │  AuroraApp          (aurora/app.py)  │
                     │  tray icon · clock manager           │
                     │  watchdog · shell-restart recovery   │
                     └──┬──────────┬───────────┬────────────┘
                        │          │           │
        ┌───────────────▼──┐  ┌────▼───────┐  ┌▼───────────────┐
        │ ClockOverlay × N │  │ SettingsUI │  │ TimeSync       │
        │ (overlay.py)     │  │            │  │ (NTP thread)   │
        └────────┬─────────┘  └────────────┘  └────────────────┘
                 │
     ┌───────────▼────────────┐        ┌──────────────────────┐
     │ faces.render()         │◀───────│ themes · sessions    │
     │ 20 faces + FX pipeline │        │ timezones · contrast │
     └───────────┬────────────┘        └──────────────────────┘
                 │
     ┌───────────▼────────────┐
     │ winutil (native Win32) │   SetWindowPos · WorkerW · TaskbarCreated
     └────────────────────────┘

                 Config (config.py) ── %APPDATA%\AuroraClock\settings.json
```

---

## Module responsibilities

| Module | Responsibility |
|---|---|
| `main.py` | Named-mutex single-instance guard, CLI flags, `QApplication` setup |
| `aurora/app.py` | `AuroraApp`: owns the config, the overlays, the tray icon, the watchdog and the native event filter |
| `aurora/overlay.py` | `ClockOverlay`: one frameless window per clock; drag/resize, the adaptive tick, the context menu |
| `aurora/faces.py` | All 20 faces plus the shared drawing pipeline (FX + gradients) |
| `aurora/themes.py` | 28 palettes; `palette(name, overrides)` resolves custom colours |
| `aurora/settings_ui.py` | The settings window and its live preview |
| `aurora/config.py` | Defaults, atomic load/save, validation, migration |
| `aurora/winutil.py` | Everything `ctypes`/Win32: Z-order, WorkerW, `TaskbarCreated`, click-through |
| `aurora/autostart.py` | The `HKCU\...\Run` value |
| `aurora/timesync.py` | NTP client on a daemon thread |
| `aurora/sessions.py` | Trading-session catalogue and the status engine |
| `aurora/alerts.py` | Alarms, chimes and session-transition alerts |
| `aurora/timezones.py` | IANA zone helpers and city labels |
| `aurora/contrast.py` | Samples the wallpaper to pick light or dark text |
| `aurora/fonts.py` | System fonts and user-imported `.ttf`/`.otf` files |
| `aurora/banner.py` | Transient on-screen notifications |

Dependencies point **inwards**: `faces` knows nothing about `app`, `config`
knows nothing about Qt widgets, and `winutil` is pure `ctypes`. That is what
lets the whole render layer be unit-tested headlessly on Linux.

---

## The window: why it is not just "always on top"

A naive overlay is a `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint` window.
That breaks in at least four ways on real Windows desktops.

### Problem 1 — the clock vanishes when Explorer restarts

A `Qt.Tool` window with `WindowStaysOnTopHint` loses its Z-order band when the
shell restarts (an Explorer crash, a theme change, `explorer.exe` being
killed). Qt never notices and the window ends up behind everything or not
composited at all.

**Fix — three layers of defence:**

1. **Native Z-order.** `winutil.apply_z_order(hwnd, mode)` calls `SetWindowPos`
   with `HWND_TOPMOST` / `HWND_NOTOPMOST` / `HWND_BOTTOM` directly, instead of
   relying on Qt flags.
2. **Shell-restart detection.** `_ShellEventFilter`, a
   `QAbstractNativeEventFilter`, listens for the `TaskbarCreated` broadcast
   message that Explorer sends when it comes back, and calls
   `recover_after_shell_restart()` about a second later (the shell needs a
   moment to settle).
3. **A watchdog timer** re-verifies position and layer every few seconds
   (configurable, default 3 s).

> After an Explorer restart the cached `WorkerW` handle is stale.
> `recover_after_shell_restart()` must reset `_wallpaper_parented = False`
> before re-attaching, or the clock re-parents to a dead window.

### Problem 2 — the clock covered the browser

Version 1.3 defaulted to *always on top*, and users hated it. Qt has **no**
"always at the bottom" window hint, so the lower layers exist purely in the
native code:

| Mode | Implementation |
|---|---|
| `top` | `SetWindowPos(HWND_TOPMOST)` |
| `normal` | `SetWindowPos(HWND_NOTOPMOST)` |
| `bottom` | `SetWindowPos(HWND_BOTTOM)` + `Qt.WindowDoesNotAcceptFocus` |
| `desktop` ⭐ default | re-parent the window to Explorer's `WorkerW`, the window that hosts the wallpaper |

The `desktop` mode is what makes the clock survive `Win`+`D` ("Show desktop") —
it is literally part of the desktop. If `WorkerW` cannot be found (some custom
shells and wallpaper apps replace it), `_apply_native()` falls back to
`Z_BOTTOM` and re-applies the geometry.

### Problem 3 — re-asserting Z-order causes flicker

Calling `SetWindowPos` with `SWP_SHOWWINDOW` every watchdog tick made the clock
flicker and burned CPU. So `apply_z_order` now pre-checks:

```python
def apply_z_order(hwnd, mode, show=True, force=False):
    if not force:
        if mode == Z_BOTTOM  and is_at_bottom(hwnd): return
        if mode == Z_TOP     and is_topmost(hwnd):   return
    ...
```

`is_at_bottom()` walks `GW_HWNDNEXT` and ignores `WorkerW`, `Progman` and
`SysShadow`, which legitimately sit below everything.

> **Rule:** only pass `force=True` from an explicit settings apply. **Never**
> from the watchdog.

### Problem 4 — clocks drifted when the mouse bumped them

The original overlay moved on any left-drag. Users lost their layout
constantly. The fix is a **double lock**:

```python
@property
def movable(self) -> bool:
    return (not self.clock.get("locked")
            and self.cfg.general.get("edit_mode")
            and not self.clock.get("click_through"))
```

Both switches must agree. The master *Edit mode* is off by default, and new
clocks start locked.

---

## The render loop: adaptive repainting

Version 1.3 ran a 25 fps timer wired straight to `update()`. Every repaint did
four shadow passes over the glyph path. For a clock showing `18:52` that is
**25 identical repaints per second**.

Version 1.4 replaced it with change detection:

```python
def _content_key(self) -> tuple:
    """Everything that affects the pixels. Unchanged key -> no repaint."""
    ...

def _tick_check(self) -> None:
    key = self._content_key()
    if key != self._last_key:
        self._last_key = key
        self.update()
```

and an interval chosen from what the face actually needs:

```python
def _needs_animation(self) -> bool:
    # a sweeping seconds hand, a blinking colon, a live countdown
    ...

def _tick_interval(self) -> int:
    return 50 if self._needs_animation() else 250
```

**Measured result: 20 repaints per 0.8 s → 2.** The clock looks identical.

| Configuration | Repaints |
|---|---|
| Digital, seconds hidden | ~1 / minute |
| Digital, seconds ticking | 1 / second |
| Analog, smooth seconds | the animation rate |

> **Do not reintroduce `self._tick.timeout.connect(self.update)`.** It
> undoes all of this.

### Quality scaling

`faces.set_fx()` reads the user's **Performance** setting and scales the
expensive work:

```python
_FX["_shadow_steps"] = {"low": 1, "balanced": 3, "smooth": 4}[quality]
```

---

## The drawing pipeline

Every face draws through one of two functions, which is why a new face gets
shadows, outlines, glow, contrast plates and gradients for free.

```
draw_path_fx(painter, path, color)        # filled glyphs
  1. contrast plate   (behind everything)
  2. drop shadow      (N offset strokes approximating a blur)
  3. glow halo        (3 widening strokes in the glow colour)
  4. outline          (a single stroke)
  5. fill             ← _fill_brush(path, color) applies the gradient

draw_shape_fx(painter, path, pen)         # stroked shapes: analog hands, bars
  shadow stroke → outline stroke → the pen itself (gradient-aware)
```

`_fill_brush()` builds a `QLinearGradient` or `QRadialGradient` over the path's
bounding rectangle, preserving the source colour's alpha so opacity still
works. When gradients are off it returns a plain `QBrush` — zero cost.

### The FX module-global

`set_fx(settings, pal, quality)` copies the current clock's settings into a
module-level `_FX` dict once per repaint. This is deliberate: it keeps every
face signature to three arguments and avoids threading a dozen effect
parameters through every helper. It is safe because **all painting happens on
the GUI thread**.

---

## Time

Aurora **never writes the system clock**. That needs administrator rights, it
affects every other program, and it is rude.

Instead, `TimeSync` measures the offset against NTP servers on a daemon thread
and the offset is applied when rendering:

```
displayed_time = (system_time + ntp_offset) → converted to the clock's zone
```

The NTP client is deliberately paranoid — leap indicator, mode, stratum and a
24-hour plausibility gate. See [SECURITY.md](../SECURITY.md) for the full
reasoning. If all servers fail, `offset = 0` and the local clock is used, so
the clock always shows *something*.

Zone conversion uses `zoneinfo`, with the `tzdata` package bundled because
Windows has no system IANA database.

---

## Sessions

`sessions.CATALOGUE` holds 17 markets, each with an open time, a close time, a
time zone and a weekday mask. `SessionStatus` objects are computed at most once
per second and cached, then handed to faces through `ctx.sessions` — so three
session faces on screen cost one computation, not three.

Alerts fire on **transitions**, detected by comparing the previous status with
the current one. A `warm_up()` call suppresses alerts for the first few seconds
after launch, so starting Aurora at 09:00 does not produce a wall of banners.

---

## Configuration

```jsonc
{
  "version": "1.5.0",
  "general":  { "edit_mode": false, "performance": "balanced", ... },
  "timesync": { "enabled": true, "servers": [...], ... },
  "alerts":   { ... },
  "ui":       { "settings_geometry": [x, y, w, h], ... },
  "clocks":   [ { "id": "clock-1", "face": "digital", ... } ]
}
```

**Load** deep-merges the file over a complete default tree, so a settings file
from an older version is upgraded automatically and a missing key is never a
`KeyError`. Then every clock is **clamped** (geometry, opacity, scale) and any
unknown `face` falls back to `digital`.

**Save** is atomic: write `settings.json.tmp`, then `os.replace()`. A power cut
cannot leave a truncated file. A corrupt file on load is moved to
`settings.json.bak` and defaults are used.

**Saves are debounced.** Dragging the opacity slider used to write the file on
every pixel; `SettingsDialog._save_soon()` coalesces writes with a 400 ms timer
and always flushes on close.

---

## The settings window

- A `QDialog` with explicit `Qt.Window | WindowMinimizeButtonHint |
  WindowMaximizeButtonHint` flags, because a plain dialog **cannot be
  minimised** — a real complaint from a real user.
- Every tab is wrapped in a `QScrollArea`, so no option is ever unreachable.
- Two `QSplitter`s: horizontal (clock list ⇄ content) and vertical
  (preview ⇄ tabs).
- A `_NoWheel` event filter stops a mouse wheel over an unfocused combo box or
  spin box from silently changing its value while the user scrolls.
- Geometry, the preview-collapsed state and the current tab are persisted under
  `data["ui"]`.

---

## Single instance

```python
CreateMutexW(None, False, "Global\\AuroraClock.SingleInstance.v1")
if GetLastError() == ERROR_ALREADY_EXISTS:   # 183
    ...
```

A kernel mutex is released automatically when the process dies, so a crash can
never leave a stale lock — unlike a PID or lock file. On POSIX there is an
`fcntl.flock` fallback so the app is still testable on Linux.

---

## Testing strategy

| Suite | Covers |
|---|---|
| `test_faces.py` | Every face × 4 window sizes × gradients × 28 themes × quality levels, plus degenerate 1×1 rectangles |
| `test_config.py` | Defaults, atomic save, corrupt files, geometry clamping, unicode, unique IDs |
| `test_timesync.py` | NTP parsing with a fake socket, every rejection path, offset measurement |
| `test_app.py` | Clock lifecycle, the double lock, screen layers, the settings window, debounced saves |
| `test_security.py` | AST-level guarantees: no `eval`/`exec`/`subprocess`/`pickle`/HTTP, atomic saves, HKCU-only, no secrets, version consistency |

All of it runs headlessly with `QT_QPA_PLATFORM=offscreen`, so CI needs no
display and no Windows for the bulk of the suite.

---

## Known limitations

| Limitation | Why |
|---|---|
| Lower Z-order modes are Windows-only | They depend on `SetWindowPos` and `WorkerW`; Linux/macOS fall back to a normal window |
| The wallpaper layer can be unavailable | Some custom shells replace Explorer's `WorkerW`; Aurora falls back to *Background* |
| Sessions ignore public holidays | They are schedule-based; a holiday calendar would need per-market data and yearly maintenance |
| Plain NTP is unauthenticated | A MITM can shift time within the 24-hour gate; disable sync if that matters to you |
| Binaries are unsigned | An Authenticode certificate costs more than this project has |
| Builds are not bit-reproducible | PyInstaller embeds timestamps and paths |
