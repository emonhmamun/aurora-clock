# Third-Party Licences

Aurora Clock itself is licensed under the
[GNU General Public License v3.0](LICENSE). It builds on the components below,
whose licences are reproduced or linked here as required.

---

## Runtime components

These are bundled inside the installer and the portable zip.

### Qt 6 / PySide6

| | |
|---|---|
| **Project** | [Qt for Python (PySide6)](https://doc.qt.io/qtforpython/) and the Qt 6 libraries |
| **Copyright** | © The Qt Company Ltd. and contributors |
| **Licence** | **LGPL-3.0** (also available commercially from The Qt Company) |
| **Used for** | The entire GUI: window management, 2D rendering, fonts, the system tray |
| **Full text** | <https://www.gnu.org/licenses/lgpl-3.0.html> |

**LGPL compliance.** Aurora Clock uses PySide6 as an unmodified library through
its public Python API. The LGPL requires that users be able to replace the
library with their own version. Because Aurora Clock is itself free software
distributed under GPL-3.0 with complete corresponding source available in this
repository, and because the Qt libraries ship as separate `.dll`/`.pyd` files
inside the application folder (not statically linked), a user can replace them
directly. No Qt source is modified by this project.

> GPL-3.0 and LGPL-3.0 are compatible: LGPL-3.0 code may be combined into a
> GPL-3.0 work.

### tzdata

| | |
|---|---|
| **Project** | [tzdata](https://pypi.org/project/tzdata/) — the IANA Time Zone Database packaged for Python |
| **Licence** | Apache-2.0 (the package); the underlying IANA database is in the public domain |
| **Used for** | Time zone and DST rules — Windows has no system IANA database |
| **Full text** | <https://www.apache.org/licenses/LICENSE-2.0> |

---

## Build-time tools

These produce the released binaries but are **not** distributed inside them.

### PyInstaller

| | |
|---|---|
| **Project** | [PyInstaller](https://pyinstaller.org/) |
| **Licence** | GPL-2.0 **with a special exception** that explicitly permits the distribution of bundled applications under any licence |
| **Used for** | Producing `AuroraClock.exe` |
| **Full text** | <https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt> |

### Inno Setup

| | |
|---|---|
| **Project** | [Inno Setup](https://jrsoftware.org/isinfo.php) by Jordan Russell |
| **Licence** | Modified BSD (allows free distribution of produced installers) |
| **Used for** | Producing `AuroraClock-Setup-x.y.z.exe` |
| **Full text** | <https://jrsoftware.org/files/is/license.txt> |

### CPython

| | |
|---|---|
| **Project** | [Python](https://www.python.org/) 3.11, embeddable distribution |
| **Licence** | PSF License Agreement (GPL-compatible) |
| **Full text** | <https://docs.python.org/3/license.html> |

---

## Fonts

Aurora Clock bundles **no font files**. It uses the fonts already installed on
your system, and any `.ttf`/`.otf` you import yourself through
Settings → Appearance → *Load .ttf…*. Imported fonts are copied to
`%APPDATA%\AuroraClock\fonts` for your own use only and are never redistributed
with the application. **You are responsible for holding a licence for any font
you import.**

---

## Icon and artwork

The Aurora Clock icon (`build_assets/aurora.ico`, `aurora.png`) is generated
programmatically by `build_assets/make_icon.py`, is original to this project,
and is covered by the same GPL-3.0 licence.

---

## Data

Trading-session times in `aurora/sessions.py` are regular published market
hours, compiled by hand from public exchange information. They are facts, not
copyrightable expression. **They are provided for convenience only, do not
account for public holidays, and must not be relied upon for trading
decisions.**

---

## Reporting a licensing problem

If you believe Aurora Clock misuses or misattributes any third-party work,
please [open an issue](https://github.com/emonhmamun/aurora-clock/issues/new/choose)
or contact the maintainer privately. It will be corrected promptly.
