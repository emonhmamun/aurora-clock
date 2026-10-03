# Configuration Reference

Everything Aurora Clock remembers lives in a single JSON file:

```
%APPDATA%\AuroraClock\settings.json
```

On Linux/macOS (development) it is `$XDG_CONFIG_HOME/AuroraClock/settings.json`
or `~/Library/Application Support/AuroraClock/settings.json`.

> **You do not need to edit this file.** Everything here is reachable from the
> settings window. This reference exists for scripting, for migrating between
> machines, and for people who like to know.

---

## Editing it safely

1. **Quit Aurora Clock first** (tray icon → Quit). It writes the file on exit
   and will overwrite your edits.
2. Keep a copy of the original.
3. Edit, save as UTF-8, and start Aurora again.

If the file cannot be parsed, Aurora moves it to `settings.json.bak`, starts
from defaults, and carries on — you will not be locked out.

### Values are validated on load

A hand-edited or corrupt file cannot break the app. On every load, each clock
is merged over a full set of defaults and then clamped:

| Field | Clamped to | Invalid value becomes |
|---|---|---|
| `width` | 80 – 8000 | the nearest bound |
| `height` | 50 – 8000 | the nearest bound |
| `x`, `y` | −10 000 – 20 000 | the nearest bound |
| `opacity` | 0.15 – 1.0 | the nearest bound |
| `scale` | 0.15 – 5.0 | the nearest bound |
| `face` | a registered face key | `"digital"` |

Missing keys are filled from the defaults, so a settings file written by an
older version keeps working.

---

## File structure

```jsonc
{
  "version":  "1.5.0",
  "first_run": false,
  "general":  { ... },      // application-wide behaviour
  "sessions": { ... },      // which markets are tracked
  "alerts":   { ... },      // alarms, chimes, notifications
  "fonts":    { ... },      // imported font files
  "timesync": { ... },      // NTP
  "ui":       { ... },      // settings-window geometry (written automatically)
  "alarms":   [ ... ],      // individual alarms
  "clocks":   [ { ... } ]   // one object per clock overlay
}
```

---

## `general`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `autostart` | bool | `true` | Mirrors the `HKCU\…\Run` entry |
| `start_minimised` | bool | `true` | Start into the tray without opening settings |
| `show_tray_icon` | bool | `true` | ⚠️ Turning this off can leave no way to reach settings — recover with `AuroraClock.exe --settings` |
| `language` | str | `"en"` | Reserved for future translations |
| `confirm_exit` | bool | `true` | Ask before quitting |
| `global_hotkey_toggle` | str | `"Ctrl+Alt+C"` | Show/hide all clocks |
| **`performance`** | str | `"balanced"` | `"low"` \| `"balanced"` \| `"smooth"` — animation rate and shadow passes (1/3/4) |
| **`edit_mode`** | bool | `false` | **The master lock.** No clock can be dragged while this is `false` |
| `lock_by_default` | bool | `true` | New clocks start with `locked: true` |
| `fade_animations` | bool | `true` | Fade clocks in and out |
| `watchdog_seconds` | int | `3` | How often position and Z-order are verified (1–30) |
| `update_interval_ms` | int | `40` | **Legacy.** Ignored since 1.4 — repainting is adaptive |

---

## `clocks[]`

Each entry is one overlay window. All keys are per-clock, so you can mix faces,
time zones, layers and locks freely.

### Identity

| Key | Type | Default | Meaning |
|---|---|---|---|
| `id` | str | `"clock-1"` | Unique, assigned automatically. **Do not duplicate it** |
| `name` | str | `"Main Clock"` | Shown in the clock list and tray menu |
| `enabled` | bool | `true` | `false` hides the clock without deleting it |

### Placement

| Key | Type | Default | Meaning |
|---|---|---|---|
| `x`, `y` | int | `80`, `80` | Top-left corner, in virtual-desktop pixels |
| `width`, `height` | int | `420`, `180` | Window size |
| `anchor` | str | `"free"` | `free` \| `top-left` \| `top` \| `top-right` \| `left` \| `centre` \| `right` \| `bottom-left` \| `bottom` \| `bottom-right` |
| `snap_margin` | int | `24` | Gap from the screen edge when snapping |
| `screen` | str | `""` | Monitor name; empty = primary/remembered |
| **`locked`** | bool | `false` | Per-clock lock. The other half of the double lock |
| `click_through` | bool | `false` | Mouse passes through; the clock cannot be right-clicked |
| **`z_mode`** | str | `"desktop"` | `"top"` \| `"normal"` \| `"bottom"` \| `"desktop"` — see below |
| `always_on_top` | bool | `false` | **Legacy**, migrated to `z_mode` |
| `show_on_all_desktops` | bool | `true` | Visible on every virtual desktop |
| `hide_when_fullscreen` | bool | `true` | Auto-hide over games and full-screen video |

#### `z_mode` values

| Value | Behaviour |
|---|---|
| `"top"` | Floats above every window |
| `"normal"` | An ordinary window |
| `"bottom"` | Always below every window |
| `"desktop"` ⭐ | Attached to the wallpaper (`WorkerW`); survives "Show desktop". Falls back to `"bottom"` if unavailable |

> **A clock moves only when** `edit_mode == true` **and** `locked == false`
> **and** `click_through == false`.

### Appearance

| Key | Type | Default | Meaning |
|---|---|---|---|
| `face` | str | `"digital"` | See [FACES.md](FACES.md) for all 20 keys |
| `theme` | str | `"aurora"` | One of the 28 theme keys |
| `opacity` | float | `0.92` | 0.15 – 1.0, whole-window |
| `scale` | float | `1.0` | 0.15 – 5.0 |
| `font_family` | str | `"Segoe UI"` | Any installed or imported family |
| `font_weight` | int | `300` | 100 – 900 |
| `custom_colors` | object | `{}` | Overrides on top of the theme, e.g. `{"fg": "#FFAA00"}`. Valid keys: `fg`, `accent`, `dim`, `bg`, `glow` |
| `background` | str | `"none"` | `"none"` \| `"glass"` \| `"panel"` \| `"solid"` |
| `corner_radius` | int | `18` | Rounds the backdrop |
| `bg_opacity` | float | `0.45` | Strength of that backdrop |
| `shadow` | bool | `true` | Master switch for the legibility effects |
| `seconds_mode` | str | `"smooth"` | `"smooth"` \| `"tick"` \| `"hidden"` — **`"hidden"` is the biggest CPU saving** |

### Legibility effects

| Key | Type | Default | Meaning |
|---|---|---|---|
| `fx_shadow` | bool | `true` | Drop shadow |
| `fx_shadow_dx`, `fx_shadow_dy` | float | `2.0` | Offset |
| `fx_shadow_blur` | float | `7.0` | `0` = a hard shadow |
| `fx_shadow_opacity` | float | `0.80` | |
| `fx_shadow_color` | str | `"#000000"` | |
| `fx_outline` | float | `0.0` | Stroke width in px; `0` = off. **The most effective readability setting** |
| `fx_outline_color` | str | `"#000000"` | |
| `fx_outline_opacity` | float | `0.95` | |
| `fx_glow` | float | `0.0` | 0.0 – 1.0 halo |
| `fx_glow_color` | str | `""` | Empty = the theme's glow colour |
| `fx_plate` | bool | `false` | Translucent plate behind the text only |
| `fx_plate_opacity` | float | `0.38` | |
| `fx_plate_color` | str | `"#000000"` | |
| `fx_plate_pad` | float | `10.0` | |
| `fx_plate_radius` | float | `10.0` | |
| `fx_auto_contrast` | bool | `false` | Pick light/dark text from the wallpaper |
| `fx_auto_strength` | float | `1.0` | |

### Gradient colouring *(new in 1.5)*

| Key | Type | Default | Meaning |
|---|---|---|---|
| `gradient_on` | bool | `false` | Master switch |
| `gradient_preset` | str | `"aurora"` | A preset key, or `"custom"` to use your own colours |
| `gradient_c1` | str | `"#38E1C6"` | Start colour (used when the preset is `"custom"`) |
| `gradient_c2` | str | `"#6C8CFF"` | End colour |
| `gradient_dir` | str | `"vertical"` | `"vertical"` \| `"vertical_r"` \| `"horizontal"` \| `"diagonal"` \| `"radial"` |
| `gradient_mid` | float | `0.5` | Position of the blended midpoint stop |
| `gradient_shapes` | bool | `true` | Also colour analog hands, rings and bars |

**Preset keys:** `custom`, `aurora`, `sunset`, `ocean`, `lime`, `gold`, `rose`,
`candy`, `fire`, `ice`, `violet`, `emerald`, `steel`, `neon`, `copper`, `mono`,
`trader`.

### Content

| Key | Type | Default | Meaning |
|---|---|---|---|
| `timezone` | str | `""` | IANA name, e.g. `"Asia/Dhaka"`. Empty = system local time |
| `label` | str | `""` | Empty = automatic city name |
| `show_label` | bool | `true` | |
| `hour24` | bool | `false` | |
| `show_seconds` | bool | `true` | |
| `show_ampm` | bool | `true` | Ignored when `hour24` is true |
| `show_date` | bool | `true` | |
| `date_format` | str | `"dddd, d MMMM yyyy"` | Tokens below |
| `blink_colon` | bool | `false` | Costs 2 repaints per second |

#### Date format tokens

| Token | Output | Token | Output |
|---|---|---|---|
| `dddd` | `Saturday` | `MMMM` | `October` |
| `ddd` | `Sat` | `MMM` | `Oct` |
| `dd` | `03` | `MM` | `10` |
| `d` | `3` | `M` | `10` |
| `yyyy` | `2026` | `yy` | `26` |

Anything else is passed through literally. The tokenizer takes the longest
match first and never rescans its own output, so `"dddd, d MMMM yyyy"` is safe.

### Session panel

| Key | Type | Default | Meaning |
|---|---|---|---|
| `show_sessions` | bool | `false` | Strip of session pills under the time |
| `session_keys` | array | `[]` | Empty = use the global `sessions.enabled` list |
| `session_style` | str | `"pills"` | `"pills"` \| `"timeline"` \| `"list"` |
| `session_countdown` | bool | `true` | Show time to the next open/close |

---

## `sessions`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | array | `["sydney","tokyo","london","newyork"]` | Market keys to track |
| `show_closed` | bool | `true` | Also list closed markets |
| `sort` | str | `"time"` | `"time"` \| `"name"` \| `"open_first"` |
| `highlight_overlap` | bool | `true` | Mark the London/New York overlap |

**Market keys:** `sydney`, `tokyo`, `london`, `newyork`, `frankfurt`,
`hongkong`, `singapore`, `dubai`, `nyse`, `nasdaq`, `lse`, `tse`, `dse`
(Dhaka SE), `nse` (India), `kz_london`, `kz_ny`, `kz_asia` (kill zones).

> Sessions follow each market's own time zone and DST rules. **Public holidays
> are not modelled.**

---

## `alerts`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `sessions_enabled` | bool | `true` | Master switch for session alerts |
| `notify_pre_open` | bool | `true` | Warn before an open |
| `notify_open` / `notify_close` | bool | `true` | On the transition |
| `notify_overlap` | bool | `true` | When an overlap begins |
| `lead_minutes` | int | `15` | How early `notify_pre_open` fires |
| `sound_session` | str | `"chime"` | Sound for session alerts |
| `sound_chime` | str | `"soft"` | Sound for the hourly chime |
| `chime` | str | `"off"` | `"off"` \| `"hour"` \| `"half"` \| `"quarter"` |
| `chime_quiet_hours` | bool | `true` | Suppress chimes overnight |
| `chime_banner` | bool | `false` | Also show a banner when chiming |
| `banner_seconds` | int | `7` | How long a banner stays |
| `tray_balloon` | bool | `true` | Use native tray notifications |

---

## `alarms[]`

```jsonc
{
  "id": "alarm-1",
  "enabled": true,
  "time": "09:30",
  "label": "London open",
  "days": [0, 1, 2, 3, 4],   // 0 = Monday … 6 = Sunday; [] = every day
  "sound": "chime",
  "repeat": true
}
```

---

## `timesync`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Poll NTP in the background |
| `servers` | array | `["time.windows.com","pool.ntp.org","time.google.com","time.cloudflare.com"]` | Tried in order; the two fastest valid replies are used |
| `interval_minutes` | int | `60` | 5 – 1440 |
| `timeout_seconds` | int | `3` | Per server |
| `max_offset_warn_ms` | int | `2000` | Warn in the UI above this |
| `apply_offset` | bool | `true` | `false` = measure but display the raw local time |
| `last_offset_ms` | float | `0.0` | Written automatically |
| `last_sync` | str | `""` | Written automatically |
| `last_server` | str | `""` | Written automatically |

> Aurora **never changes the Windows clock** — the offset is applied when
> drawing. Replies are validated and an offset over 24 hours is rejected; see
> [SECURITY.md](../SECURITY.md).

---

## `fonts`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `custom_files` | array | `[]` | Absolute paths to imported `.ttf`/`.otf` files. Copies live in `%APPDATA%\AuroraClock\fonts\` and are loaded at start-up |

---

## `ui`

Written automatically by the settings window. Safe to delete — it will be
recreated.

| Key | Type | Meaning |
|---|---|---|
| `settings_geometry` | `[x, y, w, h]` | Clamped to the visible desktop on restore |
| `settings_preview_hidden` | bool | Preview collapsed |
| `settings_tab` | int | Last open tab index |

---

## Recipes

### A minimal wallpaper clock

```jsonc
{
  "id": "clock-1", "name": "Desk",
  "face": "minimal", "theme": "pure_white",
  "x": 60, "y": 40, "width": 520, "height": 170,
  "z_mode": "desktop", "locked": true,
  "seconds_mode": "hidden", "show_date": false, "show_label": false,
  "background": "none", "fx_outline": 2.0, "opacity": 0.9
}
```

### A New York market clock with a gradient

```jsonc
{
  "id": "clock-2", "name": "NY",
  "face": "stack", "theme": "midnight",
  "timezone": "America/New_York", "label": "NEW YORK", "hour24": true,
  "x": 1500, "y": 60, "width": 300, "height": 300,
  "gradient_on": true, "gradient_preset": "trader",
  "gradient_dir": "vertical", "gradient_shapes": true,
  "show_sessions": true, "session_keys": ["nyse", "nasdaq"],
  "locked": true, "z_mode": "desktop"
}
```

### A ticker strip along the bottom edge

```jsonc
{
  "id": "clock-3", "name": "Ticker",
  "face": "ticker", "theme": "terminal",
  "x": 0, "y": 1032, "width": 1920, "height": 48,
  "anchor": "bottom", "locked": true, "click_through": true,
  "z_mode": "desktop", "seconds_mode": "tick", "opacity": 0.85
}
```

---

## Moving your setup to another PC

1. Quit Aurora on both machines.
2. Copy `%APPDATA%\AuroraClock\settings.json` (and the `fonts` folder if you
   imported any).
3. Start Aurora on the new machine.

Coordinates are absolute, so if the monitor layout differs, use
Settings → *Behaviour* → the snap grid or the monitor dropdown to re-place each
clock. Tray → *Clocks* → **Move to top-left** rescues anything off-screen.

---

## Resetting

```
AuroraClock.exe --reset
```

Starts from factory settings and keeps your old file as
`settings.json.backup`. Deleting `settings.json` by hand has the same effect
without the backup.
