# Building Aurora Clock

Three ways to get a binary, from easiest to most involved:

1. [**Let GitHub build it**](#1-let-github-build-it) — push a tag, download the artifacts.
2. [**Build on Windows**](#2-build-on-windows) — the normal developer route.
3. [**Cross-build on Linux with Wine**](#3-cross-build-on-linux-with-wine) — how
   the 1.3–1.5 releases were actually produced.

---

## Running from source (no build at all)

```bash
git clone https://github.com/emonhmamun/aurora-clock.git
cd aurora-clock
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

This works on Windows, Linux and macOS. On non-Windows platforms the native
Z-order, autostart and Explorer-recovery features are no-ops; everything else
(all 20 faces, themes, gradients, the settings window, NTP, sessions) works.

---

## 1. Let GitHub build it

The [`release.yml`](../.github/workflows/release.yml) workflow runs on a
`windows-latest` runner and produces the installer, the portable zip and
`checksums.txt`.

```bash
# maintainers
git tag -a v1.5.0 -m "Aurora Clock 1.5.0"
git push origin v1.5.0
```

The workflow then:

1. installs Python 3.11 and the pinned dependencies,
2. runs `pytest` — **a failing test blocks the release**,
3. runs PyInstaller against `build_assets/AuroraClock.spec`,
4. runs `build_assets/trim.py` to strip ~30 MB of unused Qt payload,
5. compiles the Inno Setup installer,
6. generates SHA-256 checksums,
7. uploads everything to a **draft** GitHub release for review.

You can also trigger it manually from the *Actions* tab (`workflow_dispatch`).

---

## 2. Build on Windows

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11 (64-bit) | 3.9+ works; 3.11 is what releases are built with |
| PySide6-Essentials | 6.8.1.1 | pinned for reproducibility |
| PyInstaller | 6.11.1 | pinned |
| tzdata | latest | IANA zones on Windows |
| [Inno Setup](https://jrsoftware.org/isdl.php) | 6.2.2 | only needed for the installer |

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install PySide6-Essentials==6.8.1.1 pyinstaller==6.11.1 tzdata
```

### Build the executable

```powershell
cd build_assets
pyinstaller --noconfirm --clean AuroraClock.spec
```

Output: `build_assets\dist\AuroraClock\AuroraClock.exe` (~79 MB folder).

### Trim it

```powershell
python trim.py
```

This removes roughly **29.5 MB** of payload Aurora never loads:

| Removed | Size |
|---|---|
| `opengl32sw.dll` (software OpenGL fallback) | ~20 MB |
| `d3dcompiler_47.dll` | ~4 MB |
| `Qt6Network`, `Qt6Svg`, `Qt6Qml`, `Qt6Quick`, `Qt6OpenGL`, `Qt6Pdf`, `Qt6VirtualKeyboard` | ~4 MB |
| Qt translations, `qml/`, `typesystems/`, `glue/`, `include/` | ~1 MB |
| Unused plugins (`iconengines`, `tls`, `sqldrivers`, `multimedia`, `designer`, …) | ~0.5 MB |

Image-format plugins are reduced to `qjpeg`, `qico`, `qgif` and `qwebp`, and
only the Windows platform plugin is kept. Final size: **~49 MB**.

> ⚠️ **Always launch the trimmed `AuroraClock.exe` before shipping it.** The
> excludes are aggressive. If start-up fails, the usual culprits are the
> standard-library modules PySide6's signature loader imports lazily — see
> [Troubleshooting the build](#troubleshooting-the-build).

### Build the installer

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" AuroraClock.iss
```

Output: `build_assets\AuroraClock-Setup-1.5.0.exe` (~16 MB).

### Build the portable zip

```powershell
Copy-Item ..\PORTABLE.txt dist\AuroraClock\
Compress-Archive dist\AuroraClock\* ..\AuroraClock-1.5.0-Portable.zip
```

### Checksums

```powershell
Get-FileHash AuroraClock-Setup-1.5.0.exe -Algorithm SHA256
```

---

## 3. Cross-build on Linux with Wine

This is how releases 1.3 through 1.5 were produced, and it works on a plain
Debian/Ubuntu box. It is fully scripted and takes about three minutes.

```bash
# 1. Wine with 32-bit support (needed by the Inno Setup installer stub)
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install -y wine wine64 wine32:i386 xvfb

export WINEPREFIX="$HOME/.build/wp"
export WINEDEBUG=-all
xvfb-run -a wineboot -u

# 2. Embeddable CPython (the full installer fails under Wine with c0000135)
curl -LO https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
mkdir -p "$WINEPREFIX/drive_c/Py"
unzip -o python-3.11.9-embed-amd64.zip -d "$WINEPREFIX/drive_c/Py"
cd "$WINEPREFIX/drive_c/Py"
sed -i 's/^#import site/import site/' python311._pth
echo "Lib/site-packages" >> python311._pth

# 3. pip and the build dependencies
curl -L -o gp.py https://bootstrap.pypa.io/get-pip.py
xvfb-run -a wine "C:\\Py\\python.exe" gp.py
xvfb-run -a wine "C:\\Py\\python.exe" -m pip install \
    PySide6-Essentials==6.8.1.1 pyinstaller==6.11.1 tzdata

# 4. Inno Setup 6.2.2
cd "$HOME/.build"
curl -L -o is.exe \
  https://github.com/jrsoftware/issrc/releases/download/is-6_2_2/innosetup-6.2.2.exe
xvfb-run -a wine is.exe /VERYSILENT /SP- /DIR="C:\\IS6"

# 5. Build
cd /path/to/aurora-clock/build_assets
xvfb-run -a wine "C:\\Py\\python.exe" -m PyInstaller --noconfirm --clean AuroraClock.spec
python3 trim.py
xvfb-run -a wine "C:\\IS6\\ISCC.exe" AuroraClock.iss
```

### Verifying the result under Wine

```bash
# does the trimmed exe actually start?
cd dist/AuroraClock
xvfb-run -a wine AuroraClock.exe --settings &
sleep 30 && pgrep -f AuroraClock.exe && echo "it starts"

# screenshot
sudo apt-get install -y x11-apps imagemagick
Xvfb :85 -screen 0 1400x900x24 &
DISPLAY=:85 wine AuroraClock.exe --settings &
sleep 30
DISPLAY=:85 xwd -root | convert xwd:- screenshot.png
```

### Verifying the installer under Wine

```bash
wine AuroraClock-Setup-1.5.0.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART \
     /TASKS="startupicon,desktopicon"

# expect: 645 files, an HKCU Run entry, 4 shortcuts
find "$WINEPREFIX/drive_c/users/$USER/AppData/Local/Programs/Aurora Clock" -type f | wc -l
wine reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" | grep -i aurora

# uninstall must leave nothing behind
wine "$WINEPREFIX/drive_c/users/$USER/AppData/Local/Programs/Aurora Clock/unins000.exe" \
     /VERYSILENT /SUPPRESSMSGBOXES
```

### Wine gotchas

| Problem | Fix |
|---|---|
| The full CPython installer fails with `c0000135` | Use the **embeddable** zip, as above |
| Wine refuses to create a prefix in `/tmp` | Put `WINEPREFIX` under `$HOME` |
| Inno Setup's stub will not run | Install `wine32:i386` **before** creating the prefix |
| `xwd: command not found` | `apt-get install x11-apps imagemagick` |
| `ArchitecturesAllowed=x64compatible` rejected | Inno 6.2.2 needs `x64` |
| "plugin does not support raise()", `X connection broken` | Harmless Xvfb noise |
| A Wine GUI app will not die | `pkill -f AuroraClock.exe` — never `pkill -f wine` in the same command that launched it |

---

## Build configuration reference

### `AuroraClock.spec`

| Setting | Value |
|---|---|
| `hiddenimports` | `zoneinfo`, `tzdata`, `shiboken6`, `argparse`, `logging`, `difflib`, `textwrap`, `inspect`, `typing` |
| `excludes` | Unused `PySide6.Qt*` modules plus `tkinter`, `unittest`, `sqlite3`, `email`, `http`, `multiprocessing`, `asyncio`, `ssl`, `bz2`, `lzma`, `hashlib`, … |
| `console` | `False` (GUI subsystem) |
| `icon` | `aurora.ico` |
| `version` | `version_info.txt` |

> **Never put `shiboken6.Shiboken` in `excludes`**, and always keep `shiboken6`
> in `hiddenimports` — the app will not start without it.

### `AuroraClock.iss`

| Setting | Value | Why |
|---|---|---|
| `PrivilegesRequired` | `lowest` | No UAC prompt; installs per-user |
| `PrivilegesRequiredOverridesAllowed` | `dialog` | Lets an admin choose all-users |
| `DefaultDirName` | `{autopf}\Aurora Clock` | → `%LOCALAPPDATA%\Programs` at lowest privileges |
| `AppId` | `{{9C3A7F41-…-AURORACLOCK11}` | **Change this in a fork** |
| `ArchitecturesAllowed` | `x64` | 6.2.2 does not know `x64compatible` |
| `MinVersion` | `10.0` | Windows 10+ |
| Compression | `lzma2/max`, solid | ~16 MB installer from a 49 MB payload |
| Tasks | `desktopicon`, `startupicon`, `launchnow` | `startupicon` writes the HKCU Run value and removes it on uninstall |
| `[UninstallRun]` | `taskkill /IM AuroraClock.exe /F` | So files are not locked |
| `CurUninstallStepChanged` | offers to delete `%APPDATA%\AuroraClock` | Keeps your layout if you say no |

---

## Troubleshooting the build

**`ModuleNotFoundError: No module named 'argparse'` (or `logging`, `difflib`)
at start-up**
PySide6's signature loader imports these lazily, so PyInstaller's analysis
never sees them. They must be listed in `hiddenimports`. This exact bug was hit
and fixed while building 1.5.0.

**The exe starts but no window appears**
A Qt platform plugin was trimmed. Check that
`_internal/PySide6/plugins/platforms/qwindows.dll` still exists.

**`ImportError: DLL load failed` for `shiboken6`**
`shiboken6` was excluded or is missing from `hiddenimports`.

**The installer compiles but installs nothing**
Check the `[Files]` `Source:` paths in `AuroraClock.iss` are relative to the
`.iss` file, and that `dist\AuroraClock\` exists.

**Time zones are missing at runtime**
`tzdata` must be installed in the build environment and present in
`hiddenimports`; Windows has no system IANA database.

---

## Reproducibility

Builds are not bit-for-bit reproducible — PyInstaller embeds timestamps and
paths. To verify a release independently, build from the tag and compare
behaviour and file inventory rather than hashes, or read the CI logs for the
tag, which show the exact commands and dependency versions used.
