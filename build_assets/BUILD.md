# Build assets

This folder contains everything needed to turn the Python source into the
released Windows binaries.

| File | Purpose |
|---|---|
| `AuroraClock.spec` | PyInstaller specification — hidden imports, excludes, icon, VERSIONINFO |
| `trim.py` | Post-build cleaner; removes ~29.5 MB of Qt payload Aurora never loads |
| `AuroraClock.iss` | Inno Setup script that produces the installer |
| `version_info.txt` | Windows VERSIONINFO resource embedded in the `.exe` |
| `aurora.ico` / `aurora.png` | Application icon |
| `make_icon.py` | Regenerates the icon programmatically |

**The full build instructions live in [`../docs/BUILDING.md`](../docs/BUILDING.md)** —
including the Windows route, the GitHub Actions route, and the Linux + Wine
cross-build used for the published releases.

## Quick reference

```bat
pip install PySide6-Essentials==6.8.1.1 pyinstaller==6.11.1 tzdata
cd build_assets
pyinstaller --noconfirm --clean AuroraClock.spec
python trim.py
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" AuroraClock.iss
```

> ⚠️ Always launch the **trimmed** `dist\AuroraClock\AuroraClock.exe` before
> shipping it. The excludes are aggressive, and a lazily imported standard
> library module can break start-up. CI does this check automatically.
