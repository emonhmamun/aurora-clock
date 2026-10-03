# Changelog

All notable changes to Aurora Clock are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.5.0] — 2026-10-03

The *usability and colour* release. The settings window became a proper
application window, and every face gained gradient support.

### Added

- **Gradient colouring** for every clock face — 17 presets (Sunset, Ocean,
  Fire, Liquid Gold, Rose Gold, Ultraviolet, Trader Green/Red, …), 5 directions
  (top-to-bottom, bottom-to-top, left-to-right, diagonal, radial), custom
  colour pair with a *Swap* button, and an option to colour analog hands,
  rings and bars as well.
- **6 new clock faces**: *Stacked* (hours over minutes), *Arc gauge*,
  *Neon tube*, *Minimal* (time only), *Ticker strip* (one line, for a screen
  edge) and *Dot matrix*. Total: **20**.
- **16 new themes**: Ocean Blue, Forest Green, Royal Purple, Copper,
  Cyberpunk, Ice Blue, Paper, Coffee, Mint, Lava, Steel Blue, Bubblegum,
  Terminal Green, Sand, Deep Purple, High Visibility. Total: **28**.
- **Quick text colour** swatches — 12 one-click colours in the Appearance tab.
- The settings window now **remembers its size, position and last open tab**.
- A **"Hide preview"** button and a draggable divider between the preview and
  the options.
- A full automated **test suite** (`tests/`, ~200 tests) covering rendering,
  configuration, NTP parsing, the settings window and static security
  guarantees.

### Changed

- The settings window is now a **real window**: it can be **minimised**,
  maximised, snapped and resized like any other program. A *Minimise* button
  was added next to *Close*.
- **Every settings tab now scrolls.** Options below the fold are always
  reachable, however small the window is.
- The *Clocks* list panel can be resized by dragging.
- A footer makes it explicit that **every change is applied and saved
  immediately** — there is no Apply button to hunt for.
- Minimum window size reduced to 720 × 460; default size 980 × 680.

### Fixed

- **Settings could not be minimised** and the window had no scrollbars, so
  options near the bottom of a tab were unreachable. *(Reported by a user.)*
- **Mouse wheel over a drop-down** silently changed its value while the user
  was trying to scroll the page. The wheel now scrolls the page unless the
  control has focus.
- **`settings.json` was rewritten on every pixel of a slider drag** — dozens of
  disk writes per second. Saves are now coalesced with a 400 ms debounce and
  always flushed on close.
- Setting an option to the value it already has no longer triggers a save or a
  repaint.
- `remove_clock()` no longer shows a modal dialog when called programmatically.
- Removed all unused imports and dead code (`pyflakes` is clean).

### Security

- **NTP replies are now validated** before they are trusted: the leap indicator
  must not be 3 (unsynchronised), the mode must be *server* or *broadcast*, and
  the stratum must be 1–15. A computed offset larger than 24 hours is rejected
  outright. A spoofed or broken time server can no longer shift the displayed
  time.
- **`settings.json` is sanity-checked on load.** Width/height are clamped to
  80–8000 px, X/Y to a sane range, opacity to 0.15–1.0 and scale to 0.15–5.0;
  an unknown face name falls back to *Digital*. A corrupt or hand-edited file
  can no longer create a multi-thousand-pixel window or a clock stranded
  off-screen.

---

## [1.4.0] — 2026-10-03

The *get out of my way* release, built from four problems a user reported with
a screenshot of their real desktop.

### Added

- Tray → **Clocks** submenu listing every clock, with per-clock *Show*,
  *Settings*, **Flash it so I can find it**, *Move to top-left* and
  **Delete this clock**, plus **Keep only the first clock**.
- Settings → **Keep only this one** and **Flash the selected clock** buttons,
  for untangling duplicate clocks stacked on top of each other.
- A **Performance** setting (Power saver / Balanced / Smooth) that scales the
  number of shadow passes, replacing the raw FPS spinner.
- A configurable **self-check interval** (default 3 s).
- A Windows **named-mutex single-instance guard**; launching Aurora twice now
  shows a friendly "already running — look in the tray" message.

### Changed

- **The default screen layer is now *On the wallpaper*** instead of *Always on
  top*, so the clock sits behind Chrome and every other window. It falls back
  to *below every window* automatically if the wallpaper layer is unavailable.
- Build is trimmed aggressively: `opengl32sw.dll` (~20 MB),
  `d3dcompiler_47.dll` (~4 MB), Qt Network/Svg/Qml/Quick, translations and
  unused plugins are removed. Installed size **79 MB → 52 MB**.

### Fixed

- **The clock rendered on top of the browser.** *(Reported by a user.)*
- **Adaptive repainting**: the overlay used to repaint unconditionally at
  25 fps, each repaint doing four shadow passes. It now repaints only when the
  displayed content actually changes — measured **20 → 2 repaints per 0.8 s**
  for a digital clock.
- The Z-order watchdog no longer calls `SetWindowPos` when nothing has changed,
  which removes both the wasted CPU and an occasional flicker.
- Deleting a clock now asks for confirmation.

---

## [1.3.0] — 2026-10-02

The *never lose the clock* release.

### Added

- A native Win32 **Z-order layer** (`winutil`) with four modes: always on top,
  normal, below every window, and attached to the wallpaper (WorkerW).
- An **Explorer-restart detector** — a `QAbstractNativeEventFilter` listening
  for the `TaskbarCreated` broadcast message restores the clock and the tray
  icon within a second.
- A lightweight **watchdog** that verifies position and layer periodically.
- A **double lock**: a global *Edit mode* master switch plus a per-clock
  *Lock*. A clock moves only when both allow it.
- Legibility engine: drop shadow, outline, glow, contrast plate and automatic
  light/dark text selection from the wallpaper.

### Fixed

- **The clock disappeared after a desktop refresh, `Win`+`D`, a resolution
  change or an Explorer crash.** A `Qt.Tool` window with
  `WindowStaysOnTopHint` loses its Z-order band when the shell restarts; window
  flags alone cannot fix this.
- **Clocks drifted when the mouse bumped them.** *(Reported by a user.)*

---

## [1.2.0] — 2026-10-01

### Added

- Trading-session engine: 17 markets including NYSE, Nasdaq, LSE, TSE,
  **Dhaka SE**, India NSE and the London / New York / Asia kill zones.
- Session pills, 24-hour session timeline and session board faces.
- Open/close countdowns, overlap highlighting and transition alerts.
- Alarms and hourly chimes.

---

## [1.1.0] — 2026-09-30

### Added

- Multiple simultaneous clocks, each with its own time zone and face.
- NTP time synchronisation applied at render time.
- Custom font loading (`.ttf` / `.otf`).
- Multi-monitor placement and the 9-point snap grid.

---

## [1.0.0] — 2026-09-29

First release.

### Added

- Frameless, translucent always-on-top overlay clock.
- Digital, LED, analog, flip, rings, word, binary and bars faces.
- System-tray control, settings window with a live preview.
- Autostart via the `HKEY_CURRENT_USER` Run key; position persisted between
  sessions.
- Inno Setup installer requiring no administrator rights.

---

[1.5.0]: https://github.com/emonhmamun/aurora-clock/releases/tag/v1.5.0
[1.4.0]: https://github.com/emonhmamun/aurora-clock/releases/tag/v1.4.0
[1.3.0]: https://github.com/emonhmamun/aurora-clock/releases/tag/v1.3.0
[1.2.0]: https://github.com/emonhmamun/aurora-clock/releases/tag/v1.2.0
[1.1.0]: https://github.com/emonhmamun/aurora-clock/releases/tag/v1.1.0
[1.0.0]: https://github.com/emonhmamun/aurora-clock/releases/tag/v1.0.0
