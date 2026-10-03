## What does this change?

<!-- A short description. Link the issue it closes, e.g. "Closes #42". -->

## Type of change

- [ ] 🐛 Bug fix
- [ ] ✨ New feature
- [ ] 🎨 New clock face or theme
- [ ] ⚡ Performance
- [ ] 📖 Documentation
- [ ] 🧪 Tests
- [ ] 🔧 Build / tooling
- [ ] ♻️ Refactor (no behaviour change)

## Screenshots

<!-- Required for anything visual: before and after. -->

## How was it tested?

- [ ] `pytest -q` passes
- [ ] `ruff check .` passes
- [ ] I tested it manually

**Platform tested on:** <!-- Windows 11 / Windows 10 / Linux / macOS -->

## Checklist

- [ ] My code follows the style in [CONTRIBUTING.md](../CONTRIBUTING.md)
      (PEP 8, 100 columns, type hints, British English in UI strings)
- [ ] I added or updated tests for my change
- [ ] I updated the documentation if behaviour changed
- [ ] I added an entry to `CHANGELOG.md` under `## [Unreleased]`
- [ ] I did **not** add a new runtime dependency (or I explained why below)

### If this touches rendering

- [ ] It renders correctly at 220x90, 640x280, 300x300 and 1200x160
- [ ] It respects `show_date`, `show_label`, `show_ampm`, `hour24` and
      `seconds_mode` (including `hidden`)
- [ ] It looks right in a light theme (*Paper*, *Ink*, *Sand*) as well as dark
- [ ] Gradients still work

### If this touches performance

- [ ] I did not reintroduce an unconditional repaint timer
- [ ] Repaint counts before/after:

### If this touches security

- [ ] `pytest tests/test_security.py` passes
- [ ] No new network calls, subprocesses, `eval`/`exec`, or writes outside
      `%APPDATA%` and `HKCU`

## Notes for the reviewer

<!-- Anything tricky, or decisions you are unsure about. -->
