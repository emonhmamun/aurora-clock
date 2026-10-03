# Troubleshooting

Problems are grouped by what you see. If none of this helps, please
[open an issue](../../issues/new/choose) and include your Aurora Clock version
(Settings → *Application*), your Windows build, and your `settings.json` with
any personal labels removed.

---

## The clock

### I cannot see the clock at all

Work through these in order:

1. **Is Aurora running?** Look for the clock tray icon — click the **^** arrow
   next to the Windows clock, Windows hides new icons. If it is there,
   **left-click** it: that toggles all clocks.
2. **Is the clock hidden?** Tray → **Clocks ▸** → make sure *Show this clock*
   is ticked.
3. **Is it off-screen?** This happens after unplugging a monitor. Tray →
   **Clocks ▸** → **Move to top-left**.
4. **Is the opacity at zero?** Settings → *Appearance* → **Opacity**.
5. **Nuclear option:** `Win`+`R` → `AuroraClock.exe --reset`. Your old settings
   are kept as `settings.json.backup`.

### The clock covers my browser / games / work

Tray icon → **Screen layer** → **On the wallpaper** (the default) or
**Background**.

If you want it on top *except* in games, choose *Always on top* and leave
Settings → *Behaviour* → **Hide automatically over full-screen apps and games**
ticked.

### The clock disappears when I press Win+D or refresh the desktop

Use **Screen layer → On the wallpaper**. In that mode the clock is part of the
desktop, so "Show desktop" reveals it rather than hiding it.

If it still disappears, your system may not expose Explorer's `WorkerW` window
(some custom shells and live-wallpaper apps replace it). Aurora falls back to
*Background* automatically; that mode is unaffected.

### The clock keeps moving when I touch it

Turn the **master lock** off: tray icon → **Edit mode** (untick).
Then also tick Settings → *Behaviour* → **Lock this clock's position and size**.

Both must be released before the clock can move again — that is intentional.

### I cannot move the clock

The same double lock, in reverse:

1. Tray icon → **Edit mode** → tick it **on**.
2. Settings → *Behaviour* → untick **Lock this clock's position and size**.
3. Make sure **Click-through** is off — with click-through on, the mouse passes
   straight through the clock.

### There are two clocks on top of each other and I cannot remove one

The lower one cannot be right-clicked, so use the tray:

1. Tray icon → **Clocks ▸**
2. Hover each clock → **Flash it so I can find it** (it blinks three times).
3. On the unwanted one → **Delete this clock**.

Or tray → *Clocks* → **Keep only the first clock**, or select the one you want
in Settings and press **Keep only this one**.

> At least one clock always remains. To end up with none visible, untick
> *Show this clock* instead of deleting.

### Right-clicking the clock does nothing

**Click-through** is enabled (Settings → *Behaviour*). That is what it does —
the mouse passes through. Use the **tray icon** menu instead, and untick
click-through there if you want the clock interactive again.

### The clock is blurry or the wrong size on a 4K / scaled display

Aurora is DPI-aware, but a clock placed on a 100 % monitor and then moved to a
150 % monitor keeps its pixel size. Use Settings → *Behaviour* → **Scale**, or
the **Fit face** preset, to re-fit it.

### The text is hard to read on my wallpaper

Settings → *Visibility*:

- **Outline** 2–3 px — the single most effective option.
- **Contrast plate** at ~40 %.
- **Automatic contrast** picks light or dark text from the wallpaper.
- Or switch to the **High Visibility** theme.

Use the preview backdrop buttons (*Dark / Light / Colourful / Transparency*) to
check before committing.

---

## Starting up

### It does not start with Windows

1. Settings → *Application* → **Start with Windows** should be ticked.
2. Check the registry value exists:
   ```
   HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run\AuroraClock
   ```
   It should read `"…\AuroraClock.exe" --tray`.
3. Open **Task Manager → Startup apps** and make sure *Aurora Clock* is not
   disabled there — Windows and some "optimiser" tools disable startup entries
   silently.
4. If you moved or renamed the program folder, the stored path is stale.
   Untick and re-tick *Start with Windows*.

### "Aurora Clock is already running"

That is the single-instance guard. Aurora is already there — look for the tray
icon (click the **^** arrow). If you are certain it is not running, open Task
Manager, end any `AuroraClock.exe` process, and start it again.

### Windows SmartScreen blocks the installer

The binaries are **not code-signed** — a certificate costs several hundred
dollars a year. Click **More info → Run anyway**.

If you would rather not trust an unsigned binary:

- verify the SHA-256 against `checksums.txt` on the release page, or
- [build it yourself](BUILDING.md) — it takes about three minutes.

### My antivirus flagged it

PyInstaller-packed executables are a very common false positive, because
malware authors use PyInstaller too. Aurora Clock makes no HTTP requests, spawns
no processes and contains no obfuscated code — [`tests/test_security.py`](../tests/test_security.py)
enforces that on every commit. Verify the checksum, report the false positive
to your vendor, or build from source.

---

## Settings window

### The settings window is cut off / I cannot reach the options at the bottom

Fixed in **1.5.0**. Every tab scrolls, and the window can be resized and
maximised. If you are on 1.4 or earlier, please update.

### I cannot minimise the settings window

Also fixed in **1.5.0** — there is a Minimise button in the title bar and next
to *Close*.

### Scrolling with the wheel changes a dropdown instead of scrolling

Fixed in **1.5.0**. The wheel now scrolls the page unless the control has
focus.

### Where is the Apply button?

There isn't one. **Every change is applied and saved immediately** — the
footer of the settings window says so. Just close the window when you are done.

### My settings were lost

Aurora moves a file it cannot parse to `settings.json.bak` and starts from
defaults. Look in `%APPDATA%\AuroraClock` — if `settings.json.bak` is there,
your old configuration is inside it. Close Aurora, rename it back to
`settings.json`, and reopen. If it was corrupt, open it in a text editor and
look for the damage (usually a truncated last line).

---

## Time

### The time is wrong

1. Settings → *Time & Zone* → check the **Time zone** is what you expect.
2. Check **Status** under *Internet time synchronisation* — it shows the last
   server, the measured offset and any error.
3. Press **Sync now**.
4. If the status says *implausible offset … ignored*, your PC clock is more
   than 24 hours out. Fix the Windows clock first
   (Settings → Time & language → Date & time → *Sync now*).

> Aurora **never changes your Windows clock**. It only corrects what it
> displays. Other programs will still show the wrong time until you fix the
> system clock.

### NTP sync always fails

- A firewall may be blocking **UDP port 123** outbound. Corporate networks
  often do.
- Try different servers in Settings → *Time & Zone*
  (`time.google.com`, `time.cloudflare.com`, `pool.ntp.org`).
- If it cannot be fixed, untick the sync — Aurora falls back to the Windows
  clock, which is usually fine.

### Daylight saving is wrong

Aurora uses the IANA database bundled with the app. If a government changed the
rules recently, update to the latest Aurora release (which ships a newer
`tzdata`), or report it so a release can be cut.

### Market session times look wrong

- Sessions use each market's own time zone and DST rules. During the few weeks
  when Europe and the US switch on different dates, overlaps genuinely shift.
- **Public holidays are not modelled.** A market shown as "open" may be closed
  for a holiday.

---

## Performance

### Aurora uses too much CPU

In order of impact:

1. Settings → *Time & Zone* → **Seconds** → *Hidden* or *Tick (1 s)*.
   A smooth sweeping seconds hand is by far the most expensive setting.
2. Settings → *Application* → **Performance** → *Power saver*.
3. Settings → *Visibility* → turn **Glow** off and reduce the shadow blur.
4. Use fewer clocks, and use **Fit face** so each window is as small as
   possible.
5. Settings → *Application* → raise the **self-check interval** to 10 s.

A digital clock with hidden seconds on *Power saver* repaints roughly once a
minute.

### Aurora uses too much RAM

A Qt application has a floor of roughly 50–70 MB of working set, much of it
shared Qt libraries. 1.4.0 trimmed ~30 MB of unused Qt payload from the
install. Each additional clock adds a few MB. If that is still too much for
your machine, the honest answer is that a Qt GUI is not the right tool —
Windows' own taskbar clock costs nothing.

### The clock flickers

Make sure you are on 1.4.0 or later; earlier versions re-asserted the Z-order
on every watchdog tick. If it still flickers, try a different **Screen layer**
— some third-party wallpaper apps fight over the `WorkerW` window.

---

## Uninstalling

### The uninstaller says files are in use

Close Aurora first (tray icon → **Quit**), then uninstall. The uninstaller also
runs `taskkill /IM AuroraClock.exe /F`, so this should be rare.

### Something was left behind

The uninstaller removes all program files, four shortcuts and the autostart
registry value, and *asks* whether to delete your settings. If you said no,
your settings are still at `%APPDATA%\AuroraClock` — delete that folder by hand
for a clean sweep.

---

## Collecting information for a bug report

Please include:

1. **Version** — Settings → *Application* tab.
2. **Windows version** — `Win`+`R` → `winver`.
3. **What you did, what you expected, what happened.**
4. **A screenshot**, if it is visual.
5. **Your `settings.json`** from `%APPDATA%\AuroraClock` (remove any personal
   labels first).
6. **Console output**, if you can run from source:
   ```bash
   python main.py
   ```
   That prints exceptions that the packaged GUI build swallows.

Then open an issue: [**Report a bug**](../../issues/new/choose). Thank you —
every one of the fixes in 1.4 and 1.5 came from a user report.
