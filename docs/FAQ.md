# Frequently Asked Questions

### Is it free? Really free?

Yes. Aurora Clock is free software under the **GPL-3.0** — free as in price and
free as in freedom. No ads, no "pro" tier, no account, no nag screens, no
telemetry. You can read every line of the source, change it, and share it.

### Does it work on Windows 7 / 8?

Officially no — the installer requires **Windows 10 or 11 (64-bit)**. It may
run from source on Windows 8.1, but the wallpaper (`WorkerW`) layer and some
DPI behaviour are untested there, and it is not supported.

### Does it work on Linux or macOS?

For development, yes: all 20 faces, the themes, gradients, the settings window,
NTP and sessions work. The Windows-specific layers — wallpaper Z-order,
autostart, Explorer-restart recovery, click-through — are no-ops. There is no
packaged Linux/macOS build. A well-made port would be a very welcome pull
request.

### Why does Windows warn me about the installer?

Because it is **not code-signed**. An Authenticode certificate costs several
hundred dollars a year, which this project does not have. Click
**More info → Run anyway**, verify the SHA-256 against `checksums.txt`, or
[build it yourself](BUILDING.md).

### Does it need administrator rights?

**No.** The installer uses `PrivilegesRequired=lowest` and installs into
`%LOCALAPPDATA%\Programs\Aurora Clock`. Autostart uses the per-user
`HKEY_CURRENT_USER` Run key. Nothing system-wide is touched.

### Does it send any data anywhere?

No. There is **no HTTP code path at all** — no telemetry, no analytics, no
crash reporting, no auto-updater. The only packet it ever sends is a 48-byte
UDP NTP query to the time servers you configure.
[`tests/test_security.py`](../tests/test_security.py) fails the build if anyone
adds one.

### Will it change my computer's clock?

**Never.** Aurora measures the NTP offset and applies it **when drawing the
time**. Your Windows clock, and every other program, is untouched. That is also
why it needs no admin rights.

### Why 52 MB for a clock?

Almost all of it is the Qt GUI framework. Version 1.4 already stripped ~30 MB
of Qt payload Aurora never loads. The *running* cost is what actually matters:
a digital clock repaints about twice a second — or once a minute with seconds
hidden — rather than the 25 fps a naive overlay would use.

If 52 MB on disk is unacceptable, Windows' own taskbar clock is free. That is a
genuinely fair answer.

### How much CPU and RAM does it use?

Working set is typically 50–70 MB, most of it shared Qt libraries, plus a few
MB per extra clock. CPU is near zero at idle because of adaptive repainting.
To push it lower: Seconds → *Hidden*, Performance → *Power saver*, glow off,
and use **Fit face** to shrink the window. See
[Troubleshooting → Performance](TROUBLESHOOTING.md#performance).

### How do I stop it moving when I bump the mouse?

Tray icon → **Edit mode** → off. That is the master lock, and it is off by
default. For belt and braces, also tick Settings → *Behaviour* →
**Lock this clock's position and size**. Both must be released to move it
again.

### Why is my clock behind Chrome?

Because that is the default, and most people want it. Tray icon →
**Screen layer** → **Always on top** if you want it in front.

### How do I get rid of a duplicate clock?

Tray icon → **Clocks ▸** → hover a clock → **Flash it so I can find it** →
**Delete this clock**. Or **Keep only the first clock**. Full details in the
[User Guide](USER_GUIDE.md#removing-duplicate-clocks).

### Can I have more than one clock?

As many as you like, each with its own face, theme, time zone, size, position,
monitor and lock state. **Duplicate** in the settings window copies a clock
with all its settings — handy for a row of world clocks.

### Can I put a clock on each monitor?

Yes. Add a clock, then Settings → *Behaviour* → the monitor dropdown, or just
drag it across with Edit mode on.

### Can I use my own font?

Settings → *Appearance* → **Load .ttf…**. The file is copied into
`%APPDATA%\AuroraClock\fonts` so it keeps working after a restart, and even if
you later move the original.

### Can I make my own clock face or theme?

Yes, and please do — it is the most welcome kind of contribution. A face is a
single function; a theme is one dictionary entry. See
[CONTRIBUTING.md](../CONTRIBUTING.md#writing-a-new-clock-face).

### Where are my settings stored?

`%APPDATA%\AuroraClock\settings.json`. Every key is documented in
[CONFIGURATION.md](CONFIGURATION.md). Copy that file to move your setup to
another PC.

### I broke my settings. How do I start over?

`AuroraClock.exe --reset`. Your old file is kept as `settings.json.backup`.

### Does it support time zones and daylight saving?

Yes — any IANA zone, with DST handled automatically through `zoneinfo`. The
`tzdata` database is bundled because Windows does not ship one.

### Do the trading sessions account for public holidays?

**No.** Sessions are schedule-based and follow each market's regular hours and
DST rules. A market shown as "open" may be closed for a holiday. Adding a
holiday calendar would require per-market data and yearly maintenance — a
contribution would be welcome.

### Is the Dhaka Stock Exchange supported?

Yes, `dse` is one of the 17 built-in sessions, alongside NSE India, NYSE,
Nasdaq, LSE, TSE and the three kill zones.

### Can it run from a USB stick?

Yes — download the **Portable** zip. Nothing is written outside the folder
except `%APPDATA%\AuroraClock\settings.json`. For autostart, put a shortcut
with the `--tray` argument into `shell:startup`.

### How do I update?

Download the new installer and run it over the top — your settings are kept.
There is deliberately no auto-updater; nothing on your machine downloads or
executes code after installation. Watch the
[releases page](../../releases) to be notified.

### My antivirus flagged it

PyInstaller-packed executables are a frequent false positive, because malware
authors use PyInstaller too. Aurora makes no HTTP requests, spawns no
processes and contains no obfuscated code. Verify the checksum, report the
false positive to your vendor, or build from source.

### Can I use Aurora Clock at work / commercially?

Yes. The GPL places no restriction on *using* the software, for any purpose,
including commercially.

### Can I modify it and give it to other people?

Yes — that is the point. The condition is that you must **publish your modified
source code under GPL-3.0 as well**, so that whoever receives your version has
the same freedoms you had. See the [LICENSE](../LICENSE).

### Can I sell it?

The GPL allows you to charge for distribution. But you must still provide the
complete corresponding source under GPL-3.0, and your customers may then
redistribute it for free. In practice that makes selling it as closed software
impossible — which is intentional.

### Can I use parts of the code in my closed-source app?

No. GPL-3.0 is copyleft: a derivative work must also be GPL-3.0. If you need a
different arrangement, open an issue and ask.

### Who made this?

Built by [@emonhmamun](https://github.com/emonhmamun), with features driven
directly by user reports — versions 1.3, 1.4 and 1.5 each exist because
somebody said "this is annoying" and was right.

### How do I report a bug or ask for a feature?

[Open an issue](../../issues/new/choose). For bugs, please include the version
(Settings → *Application*), your Windows build, and a screenshot if it is
visual. For security problems, use
[private reporting](../../security/advisories/new) instead — see
[SECURITY.md](../SECURITY.md).
