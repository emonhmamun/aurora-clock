# Aurora Clock — User Guide

Everything the program can do, in the order you are likely to need it.

- [First run](#first-run)
- [Placing and locking your clock](#placing-and-locking-your-clock) ← start here
- [Choosing a screen layer](#choosing-a-screen-layer)
- [The tray menu](#the-tray-menu)
- [The settings window](#the-settings-window)
  - [Appearance](#appearance-tab)
  - [Visibility](#visibility-tab)
  - [Time & Zone](#time--zone-tab)
  - [Sessions](#sessions-tab)
  - [Alerts](#alerts-tab)
  - [Behaviour](#behaviour-tab)
  - [Application](#application-tab)
- [Working with several clocks](#working-with-several-clocks)
- [Removing duplicate clocks](#removing-duplicate-clocks)
- [Recipes](#recipes)
- [Keyboard and mouse reference](#keyboard-and-mouse-reference)
- [Where your data lives](#where-your-data-lives)
- [Uninstalling](#uninstalling)

---

## First run

After installation Aurora Clock starts automatically and shows:

- **one clock** in the top-left corner of your main monitor, and
- a **tray icon** (a small clock) in the notification area.

If you cannot see the tray icon, click the **^** arrow next to the Windows
clock — Windows hides new icons by default. Drag it onto the visible part of
the taskbar so it is always one click away.

> The clock sits **on the wallpaper layer**, which means other windows cover
> it. That is intentional. If you want it floating over everything, see
> [Choosing a screen layer](#choosing-a-screen-layer).

---

## Placing and locking your clock

This is the one workflow everybody needs. Aurora deliberately makes it
impossible to move a clock by accident, so there is a switch to flip first.

### Step 1 — Turn on Edit mode

Right-click the **tray icon** → **Edit mode** (tick it on).

While Edit mode is on, clocks can be dragged and resized. A subtle outline
appears when you hover over one.

### Step 2 — Drag it into place

Drag the clock with the left mouse button. Three alternatives if you want
precision:

| Method | Where |
|---|---|
| **Snap to a corner or edge** | Settings → *Behaviour* → the 9-point snap grid |
| **Exact coordinates** | Settings → *Behaviour* → the X / Y / W / H boxes |
| **Move to another monitor** | Settings → *Behaviour* → monitor dropdown |

### Step 3 — Set the size

| Method | Where |
|---|---|
| **Drag an edge or corner** of the clock (Edit mode on) | on screen |
| **Size presets** — S, M, L, XL, Square, Fit face | Settings → *Behaviour* |
| **Scale slider** — 15 % to 500 % | Settings → *Behaviour* |

> **Tip:** *Fit face* shrinks the window to the clock that is actually drawn.
> A smaller window means less to repaint, so it is the cheapest setting on a
> laptop battery.

### Step 4 — Turn Edit mode off

Right-click the **tray icon** → **Edit mode** (untick it).

**The clock can now never be moved by the mouse.** Clicks pass over it; a
bumped trackpad cannot nudge your layout.

### Step 5 — (Optional) Lock the individual clock

Settings → *Behaviour* → tick **Lock this clock's position and size**.

This is the second half of the **double lock**. A clock moves only when:

```
Edit mode is ON   AND   that clock is not Locked   AND   Click-through is off
```

To move it again later you must release **both** locks.

---

## Choosing a screen layer

Right-click the **tray icon** → **Screen layer**, or Settings → *Behaviour* →
*Screen layer*.

| Layer | Behaviour | Good for |
|---|---|---|
| **Always on top** | Floats over Chrome, games, everything. | A countdown you must not miss |
| **Normal** | Behaves like an ordinary window; can be covered and raised. | Occasional reference |
| **Background** | Always below every window; reappears the moment you minimise. | A tidy desktop |
| **On the wallpaper** ⭐ *default* | Becomes part of the desktop itself, so even `Win`+`D` ("Show desktop") leaves it visible. | Almost everyone |

> If the wallpaper layer is not available on your system — some custom shells
> and wallpaper apps replace Explorer's `WorkerW` window — Aurora falls back to
> *Background* automatically. You do not need to do anything.

**Also useful:** *Hide automatically over full-screen apps and games* (on by
default) keeps the clock out of your games and video.

---

## The tray menu

Right-click the tray icon:

| Item | What it does |
|---|---|
| **Edit mode** | The master lock. Off = nothing can be dragged. |
| **Clocks ▸** | Every clock, with per-clock actions (see below). |
| **Screen layer ▸** | The four layers above. |
| **Settings…** | Opens the settings window. |
| **Sync time now** | Forces an immediate NTP check. |
| **Start with Windows** | Toggles the autostart entry. |
| **About** | Version and licence. |
| **Quit** | Closes Aurora Clock completely. |

**Left-click** the tray icon to show or hide all clocks at once.

Inside **Clocks ▸**, each clock offers:

| Action | Use |
|---|---|
| *Show this clock* | Hide one clock without deleting it |
| *Settings…* | Jump straight to that clock's options |
| **Flash it so I can find it** | Blinks the clock three times — the fastest way to tell two clocks apart |
| *Move to top-left* | Rescue a clock that ended up off-screen |
| **Delete this clock** | With a confirmation prompt |
| **Keep only the first clock** | Emergency cleanup |

---

## The settings window

Open it from the tray menu, the Start-menu shortcut *Aurora Clock Settings*, or
`AuroraClock.exe --settings`.

**Things worth knowing:**

- **Every change is applied and saved immediately.** There is no Apply button.
- The window **minimises, maximises, resizes and snaps** like any other program
  (there is also a *Minimise* button next to *Close*).
- **Every tab scrolls** — use the scrollbar on the right, the mouse wheel over
  empty space, or `Page Down`.
- A **mouse wheel over a dropdown scrolls the page**, it does not change the
  value. Click a dropdown first if you want to change it.
- **Hide preview** gives the options the whole window, and you can drag the
  divider between the preview and the tabs.
- The window remembers its size, position and the tab you were last on.
- The preview backdrop buttons — *Theme / Dark / Light / Colourful /
  Transparency* — let you check that your clock stays readable on any
  wallpaper **before** you commit to it.

### Appearance tab

| Option | Notes |
|---|---|
| **Clock name** | Only used in the clock list and tray menu. |
| **Clock face** | All 20 faces — see [FACES.md](FACES.md). |
| **Theme** | 28 palettes. *Paper*, *Ink* and *Sand* are designed for light wallpapers. |
| **Font** | Any font installed on your PC. **Load .ttf…** imports your own; it is copied into Aurora's folder, so it survives restarts and moves. |
| **Font weight** | 100 (hairline) – 900 (black). Not every font has every weight. |
| **Background** | *Transparent*, *Glass*, *Soft panel*, *Solid* — a backdrop behind the clock. |
| **Corner radius** | Rounds that backdrop. |
| **Opacity** | 15 % – 100 % for the whole clock. |
| **Glow / shadow** | The quick on/off for the legibility effects. |
| **Custom colours** | Override *Text*, *Accent*, *Secondary* or *Panel* on top of the theme. *Reset colours* returns to the theme. |
| **Quick text colour** | 12 one-click swatches. |

#### Gradient colouring

Tick **Paint the clock with a colour gradient** to unlock it.

| Option | Notes |
|---|---|
| **Preset** | 17 gradients: Aurora, Sunset, Ocean, Lime Punch, Liquid Gold, Rose Gold, Cotton Candy, Fire, Ice, Ultraviolet, Emerald, Brushed Steel, Neon Split, Copper, Silver Fade, **Trader Green/Red**, or *Custom*. |
| **Direction** | Top→bottom, bottom→top, left→right, diagonal, or centre-outwards (radial). |
| **Own colours** | *Colour 1* / *Colour 2* pickers, plus **Swap**. Choosing a colour switches the preset to *Custom* automatically. |
| **Also colour hands, bars and rings** | Extends the gradient to analog hands and bar/ring faces, not just text. |

Gradients work on **all 20 faces**, because every face draws through the same
pipeline.

### Visibility tab

The legibility engine — this is what keeps the clock readable on a busy
photo wallpaper.

| Option | Notes |
|---|---|
| **Drop shadow** | Offset, blur, opacity and colour. On by default. |
| **Outline** | A stroke around the glyphs. Width 0 turns it off. The single most effective setting on a noisy wallpaper. |
| **Glow** | A soft halo in the theme's glow colour. |
| **Contrast plate** | A translucent plate behind the text only (not the whole window). Padding, radius, colour and opacity are adjustable. |
| **Automatic contrast** | Samples your wallpaper and picks light or dark text for you. |
| **Presets** | One-click combinations for common situations. |

### Time & Zone tab

| Option | Notes |
|---|---|
| **Time zone** | *System local time*, a popular zone, or any IANA zone (the list is searchable). DST is handled automatically. |
| **Label** | Leave empty for the automatic city name. |
| **24-hour clock** / **Show AM/PM** / **Show label** / **Show date** | Self-explanatory. |
| **Date format** | Pick a preset or type your own: `dddd`, `ddd`, `dd`, `d`, `MMMM`, `MMM`, `MM`, `M`, `yyyy`, `yy`. |
| **Seconds** | *Smooth sweep*, *Tick (1 s)* or *Hidden*. **Hidden or Tick uses noticeably less CPU than a smooth sweep.** |
| **Blinking colon** | Classic digital-clock behaviour. |

#### Internet time synchronisation

Aurora measures the difference between your PC clock and a pool of NTP servers
and applies that offset **when drawing the time**. Your Windows clock is never
modified, so no administrator rights are needed and nothing else on your system
is affected.

| Option | Notes |
|---|---|
| **Keep the displayed time accurate automatically** | On by default. |
| **Check every** | 5 – 1440 minutes. 60 is plenty. |
| **Status** | Last server used, the measured offset and any error. |
| **Sync now** | Forces an immediate check. |

If every server fails, Aurora quietly falls back to your local clock and shows
the error in *Status*. Offsets larger than 24 hours are rejected as implausible.

### Sessions tab

For traders. Pick the markets you care about from 17 presets:

**FX centres:** Sydney · Tokyo · London · New York · Frankfurt · Hong Kong ·
Singapore · Dubai
**Exchanges:** NYSE · Nasdaq · London SE · Tokyo SE · **Dhaka SE** · India NSE
**Kill zones:** London · New York · Asia

| Option | Notes |
|---|---|
| **Session strip** | Shows pills under the time on any ordinary face. |
| **Style** | *Pills*, *Timeline* or *List*. |
| **Countdown** | Time until the next open or close. |
| **Highlight overlaps** | The London/New York overlap is marked. |
| **Sort order** | By time or by name. |

Three faces are built entirely around this data: **Trader dashboard**,
**Session timeline (24 h)** and **Session board**.

> All session times use each market's own time zone and follow its DST rules.
> They are schedule-based and do **not** know about public holidays.

### Alerts tab

| Option | Notes |
|---|---|
| **Session alerts** | A desktop banner when a market opens or closes. |
| **Hourly chime** | On the hour. |
| **Alarms** | Add any number of one-off or repeating alarms with a label and chosen weekdays. |
| **Banner position / duration** | Where notifications appear and for how long. |

Alerts fire on **transitions only** and are suppressed for a few seconds after
startup, so launching Aurora at 09:00 does not flood you with banners.

### Behaviour tab

| Option | Notes |
|---|---|
| **Edit mode** (master lock) | See [Placing and locking](#placing-and-locking-your-clock). |
| **New clocks start locked** | Recommended. |
| **Lock this clock's position and size** | The per-clock half of the double lock. |
| **Click-through** | The mouse passes straight through to whatever is behind the clock. The clock becomes decoration. ⚠️ You cannot right-click it any more — use the tray menu. |
| **Screen layer** | The four layers. |
| **Hide automatically over full-screen apps and games** | On by default. |
| **Show this clock** | Hide a clock without deleting it. |
| **Geometry** | Exact X, Y, W, H. |
| **Size presets** | S / M / L / XL / Square / **Fit face**. |
| **Scale** | 15 % – 500 %. |
| **Snap to** | The 9-point grid, with an adjustable margin. |
| **Monitor** | Move the clock to another display. |

### Application tab

| Option | Notes |
|---|---|
| **Start with Windows** | Writes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. No admin rights, no scheduled task. |
| **Show tray icon** | ⚠️ Turning this off with no clocks visible leaves no way to reach the settings. Use `AuroraClock.exe --settings` to recover. |
| **Performance** | *Power saver* / *Balanced* / *Smooth* — controls animation rate and the number of shadow passes. |
| **Self-check interval** | How often Aurora verifies the clock is still in the right place and layer (default 3 s). |
| **Version / licence** | Also where to find the settings folder. |

---

## Working with several clocks

Add a clock with Settings → **Add**, or tray → *Clocks* → *Add a clock*.

Each clock is completely independent: its own face, theme, time zone, size,
position, monitor, lock state and screen layer. Common setups:

- A large local clock, plus small **New York** and **London** clocks for market
  hours.
- A *Ticker strip* along the bottom edge and an *Analog* clock in a corner.
- One clock per monitor.

**Duplicate** copies the selected clock including all of its settings — the
fastest way to build a row of world clocks.

---

## Removing duplicate clocks

If two clocks end up stacked on top of each other, the lower one cannot be
right-clicked. Use either route:

**From the tray (works even when clocks overlap exactly):**

1. Tray icon → **Clocks ▸**
2. Hover a clock → **Flash it so I can find it** — it blinks three times so you
   know which is which.
3. → **Delete this clock**, and confirm.

**From the settings window:**

1. Select the clock you want to *keep* in the left-hand list.
2. Click **Keep only this one** — every other clock is removed.

There is also tray → *Clocks* → **Keep only the first clock** as a one-click
reset. At least one clock always remains; if you want zero visible clocks,
untick *Show this clock* instead.

---

## Recipes

### A clean wallpaper clock that never covers anything

Face *Minimal* or *Stacked* · Theme *Pure White* · Background *Transparent* ·
Outline 2 px · Screen layer **On the wallpaper** · Seconds *Hidden* ·
Performance *Power saver* · Edit mode **off** + **Locked**.

### A trader's cockpit

Clock 1: face *Trader dashboard*, time zone *System local time*, sessions
London + New York + Tokyo + DSE, countdown on, overlaps highlighted.
Clock 2: face *Ticker strip* along the bottom edge, time zone *America/New_York*.
Alerts: session alerts on.
Gradient: *Trader Green/Red*, direction *left to right*.

### Maximum readability on a photo wallpaper

Theme *High Visibility* · Outline 3 px · Contrast plate on at ~40 % ·
Drop shadow blur 10 · Automatic contrast on. Check it against the **Colourful**
preview backdrop.

### Lowest possible resource usage

Face *Digital* or *Minimal* · Seconds **Hidden** · Performance **Power saver** ·
Glow off, outline off, plate off · *Fit face* to shrink the window ·
Self-check interval 10 s. A digital clock with hidden seconds repaints roughly
**once a minute**.

---

## Keyboard and mouse reference

| Input | Effect |
|---|---|
| Left-click tray icon | Show / hide all clocks |
| Right-click tray icon | The main menu |
| Right-click a clock | That clock's quick menu *(unless click-through is on)* |
| Drag a clock | Move it *(Edit mode on, not locked)* |
| Drag a clock edge/corner | Resize *(Edit mode on, not locked)* |
| `Page Up` / `Page Down` in settings | Scroll the current tab |
| `Ctrl`+`Tab` in settings | Next tab |
| `Esc` in settings | Close (the layout is still saved) |

---

## Where your data lives

| What | Where |
|---|---|
| Settings | `%APPDATA%\AuroraClock\settings.json` |
| Imported fonts | `%APPDATA%\AuroraClock\fonts\` |
| Backup of a corrupt file | `%APPDATA%\AuroraClock\settings.json.bak` |
| Backup made by `--reset` | `%APPDATA%\AuroraClock\settings.json.backup` |
| Program files | `%LOCALAPPDATA%\Programs\Aurora Clock\` |
| Autostart entry | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\AuroraClock` |

Paste `%APPDATA%\AuroraClock` into the Explorer address bar to get there.

**To move your setup to another PC**, copy `settings.json` (and the `fonts`
folder) across. Coordinates are absolute, so check the placement if the new
machine has a different monitor layout.

**If everything goes wrong**, run `AuroraClock.exe --reset`. Your old file is
kept as `settings.json.backup`.

---

## Uninstalling

**Settings → Apps → Aurora Clock → Uninstall**, or the *Uninstall Aurora Clock*
Start-menu shortcut.

The uninstaller removes every program file, all four shortcuts and the
autostart registry entry, and then **asks** whether you also want to delete
your settings folder — so you can reinstall later and keep your layout.

For the portable edition, just delete the folder (and `%APPDATA%\AuroraClock`
if you want a clean sweep).
