# CLAUDE.md — guide for AI assistants working on DOCKIT

DOCKIT (Device and Operational Control Kit for Integrated Tuning) is an open-source
(GPL-3.0-or-later) Linux laptop control panel, a replacement for Gigabyte GiMATE. First target
machine: Gigabyte Gaming A16 3VH (Ryzen 7 260, RTX 5060). It must work across desktops:
Hyprland, niri, Sway, KDE Plasma, X11 (GNOME partially).

## About the owner
- GitHub `aktirf` (AkTirF). A beginner / "vibecoder": explain steps plainly, give exact
  commands, never assume terminal experience. Writes Russian: answer in Russian unless asked.
- Tests on a real laptop with CachyOS. The desktop changes over time (Hyprland 0.57 with end-4
  dots, now KDE Plasma): ask which one is running before giving desktop-specific steps.
  Do not edit the user's own desktop config files unless asked.
- If you cannot run the GUI (no PySide6 / no display), say so. Never claim a QML change was
  visually verified; the owner tests and sends logs or screenshots.

## Layout (src layout, Python 3.11+, no runtime dependencies in the core)
- `src/dockit/core/` — pure logic: scanner, profiles (TOML rules), display (refresh rate per
  desktop: niri, Hyprland, Sway, KDE `kscreen-doctor`, X11 `xrandr`), audio, bluetooth,
  processes, tuning, idle. Parsers are separate functions so they can be unit-tested with
  sample text.
- `src/dockit/modules/` — one feature per file, subclass of `core/module.py:Module` with
  `detect()` / `get_state()` / `fix_hint()`. `detect()` and `get_state()` only READ and never raise.
- `src/dockit/daemon/` — root service (Unix socket `/run/dockit/dockit.sock`). Accepts only
  a fixed list of actions (`actions.py`), validates every value, never takes a path from the
  client, checks polkit with the real PID from the socket. Policy: `data/polkit/org.dockit.policy`.
  A new write action needs ALL of: action in `actions.py`, protocol entry, polkit action, test.
- `src/dockit/gui/` — PySide6 + Qt Quick. `backend.py` (QObject, worker threads, signals),
  `viewmodel.py` (pure dicts, testable), `qml/` pages. `SyncModel.qml` updates lists in place
  (replacing a model on every refresh rebuilds delegates and makes the UI jerk).
- `src/dockit/cli/` — `dockit scan | report | mode | auto | profile | camera | gui | daemon`.
- `devices/` — plain-text device database (matched by USB ID / BIOS model). See `devices/README.md`.
- `scripts/` — `install.sh` (deps + install), `install-dev.sh`, `uninstall-dev.sh`, `probe.sh`.
- `packaging/arch/` — PKGBUILD.

## Rules
1. The core must not import Qt. GUI shows data from `viewmodel.py`; keep logic out of QML.
2. Reading is free; any write goes through the daemon with a confirmation. Never add a
   shell-command or arbitrary-path action to the daemon.
3. QML: guard against `null` / `undefined` (`!!(...)` for bools, `String()`/`Number()` for
   text/numbers). Warnings in the log are real bugs. Give every object a unique `id`.
4. Hyprland 0.55+ uses a Lua config: `hyprctl keyword` is rejected (exit code 0!). Apply
   runtime changes with `hyprctl eval 'hl.monitor({...})'`; the code detects the parser with
   `hyprctl eval 'return 1'`. Keep the legacy `keyword` path for old `.conf` setups.
5. Unknown hardware: show the state honestly ("not available") with `fix_hint()`; do not guess.
6. UI text is Russian (English UI is planned); code, comments and commits are English.
7. Add a unit test for every parser and every rule (tests use sample text, no real hardware).

## Commands
```bash
python -m venv .venv && source .venv/bin/activate && pip install -e . pytest
python -m pytest -q                  # all tests must pass (no hardware needed)
dockit scan                          # read-only hardware scan
sudo scripts/install-dev.sh          # install the service + app into /opt/dockit (testing)
dockit gui                           # open the window
```

## Git workflow
- Never push to `main`. Branch → push → PR; the owner merges ("Create a merge commit").
- Stacked PRs: base every PR on `main`, otherwise it merges into a side branch.
- `gh` GraphQL is unavailable in some sessions; use `gh api repos/aktirf/dockit-panel/...`.
- Commit messages in English, short first line, then what and why.
