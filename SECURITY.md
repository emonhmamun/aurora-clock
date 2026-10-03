# Security Policy

Aurora Clock starts automatically with Windows and sits on your desktop all
day. That is a position of trust, so the project treats security as a feature,
not an afterthought.

---

## Supported versions

| Version | Supported |
|---|---|
| 1.5.x | ✅ Yes |
| 1.4.x | ⚠️ Critical fixes only |
| ≤ 1.3 | ❌ No — please upgrade |

---

## Reporting a vulnerability

**Please do not open a public issue for a security problem.**

Use GitHub's private reporting instead:

👉 **[Report a vulnerability privately](https://github.com/emonhmamun/aurora-clock/security/advisories/new)**

Please include:

- the Aurora Clock version (Settings → *Application* tab) and your Windows build,
- what an attacker could achieve,
- reproduction steps or a proof of concept,
- any suggested fix.

**What to expect**

| Stage | Target |
|---|---|
| Acknowledgement | within 72 hours |
| Initial assessment | within 7 days |
| Fix released | within 30 days for high severity |

You will be credited in the release notes unless you prefer to stay anonymous.
This is a free, unfunded project, so there is no bug bounty — but your work
will be acknowledged properly.

---

## Threat model

### What Aurora Clock deliberately does *not* do

| | |
|---|---|
| ❌ No administrator rights | The installer uses `PrivilegesRequired=lowest` and installs into `%LOCALAPPDATA%\Programs`. |
| ❌ No `HKEY_LOCAL_MACHINE` writes | Autostart uses the per-user `HKCU\...\Run` key only. |
| ❌ No system clock changes | The NTP offset is applied **at render time**. Your Windows clock is never written to. |
| ❌ No HTTP, no telemetry, no analytics | There is no outbound HTTP code path at all. |
| ❌ No auto-updater | Nothing downloads or executes code after installation. |
| ❌ No `eval` / `exec` / `subprocess` / shell | There is no dynamic code execution anywhere in the codebase. |
| ❌ No `pickle` / `marshal` / `yaml.load` | Settings are plain JSON; no deserialisation can execute code. |
| ❌ No elevated services or scheduled tasks | Aurora is one ordinary user-level process. |

All of the above are enforced by automated tests in
[`tests/test_security.py`](tests/test_security.py), which run in CI on every
push. A pull request that breaks one of these guarantees fails the build.

### Attack surface

Aurora Clock's entire externally-influenced input consists of:

1. **NTP replies** (UDP port 123) from the servers you configure.
2. **`settings.json`** in `%APPDATA%\AuroraClock`.
3. **Font files** you explicitly import, parsed by Qt.

Each is hardened:

#### 1. NTP

A hostile or broken time server could otherwise make your clock show the wrong
time (which, for a trader watching market sessions, matters). Every reply must
pass:

- length ≥ 48 bytes,
- leap indicator ≠ 3 (`3` means the server is itself unsynchronised),
- mode ∈ {4 server, 5 broadcast},
- stratum within 1–15,
- the resulting offset must be **< 24 hours**, otherwise it is discarded and
  reported as an error in the UI.

The socket has a hard timeout, reads a fixed 48 bytes, and the parsing is pure
`struct.unpack` with no allocation based on attacker-controlled length. The
sync runs on a daemon thread and any failure degrades gracefully to "use the
local clock".

> **Known limitation:** plain NTP is unauthenticated by design. A
> machine-in-the-middle on your network can still shift the time *within* the
> 24-hour window. If that is in your threat model, disable internet time sync
> (Settings → *Time & Zone*) and rely on the Windows Time service.

#### 2. Settings file

`settings.json` is read with `json.load` (no code execution). On load, every
clock is merged over a complete set of defaults and then clamped:

| Field | Accepted range |
|---|---|
| `w`, `h` | 80 – 8000 px |
| `x`, `y` | −10 000 – 20 000 px |
| `opacity` | 0.15 – 1.0 |
| `scale` | 0.15 – 5.0 |
| `face` | must be a registered face, else *Digital* |

A corrupt file is moved aside to `settings.json.bak` and defaults are used, so
Aurora always starts. Saves are **atomic** (`write` to `.tmp` → `os.replace`),
so a power cut cannot truncate your configuration.

#### 3. Fonts

Imported fonts are copied into `%APPDATA%\AuroraClock\fonts` and registered
with `QFontDatabase.addApplicationFont`. Parsing is handled by Qt/FreeType. A
malicious font is a Qt-level risk, not an Aurora-level one; keep PySide6 up to
date, and only import fonts you trust.

---

## Verifying what you downloaded

Every release ships a `checksums.txt`. Verify before running:

```powershell
Get-FileHash .\AuroraClock-Setup-1.5.0.exe -Algorithm SHA256
```

Compare the result with the value in `checksums.txt` on the release page.

**The binaries are not code-signed.** An Authenticode certificate costs several
hundred dollars a year, which this project does not have, so Windows SmartScreen
will show a warning. If you would rather not trust a prebuilt binary at all:

- build it yourself — see [docs/BUILDING.md](docs/BUILDING.md), or
- read [`.github/workflows/release.yml`](.github/workflows/release.yml), which
  builds the published artifacts on GitHub's runners from the tagged source.

---

## Dependencies

| Component | Licence | Why it is here |
|---|---|---|
| [PySide6](https://doc.qt.io/qtforpython/) (Qt 6) | LGPL-3.0 | GUI toolkit and rendering |
| [tzdata](https://pypi.org/project/tzdata/) | Apache-2.0 / public domain | IANA time zone database on Windows |
| [PyInstaller](https://pyinstaller.org/) *(build only)* | GPL-2.0 with exception | Produces the `.exe` |
| [Inno Setup](https://jrsoftware.org/isinfo.php) *(build only)* | Modified BSD | Produces the installer |

Dependencies are pinned in `requirements.txt` / the build workflow. Please
report any CVE affecting them through the process above.

---

## Hardening checklist for packagers and forks

If you redistribute a modified Aurora Clock:

- [ ] Keep the GPL-3.0 licence and publish your source (it is required).
- [ ] Do not add telemetry without a clear, opt-in prompt.
- [ ] Do not raise the installer to admin privileges.
- [ ] Keep `tests/test_security.py` in your CI, and keep it passing.
- [ ] Re-generate `checksums.txt` for your own builds.
- [ ] Change the `AppId` GUID in `AuroraClock.iss` so your installer does not
      overwrite upstream installations.
