# DOCKIT

**Device and Operational Control Kit for Integrated Tuning**

A control panel for Linux laptops that shows what works on **your** machine, what does not, and how to fix it.

> Status: early development. Right now there is a scanner (read-only), USB device recognition with a device database, a background service for two changes (performance mode, camera) and a command line. The window (UI) is planned.
> Unofficial project. Not affiliated with Gigabyte, EPOS, Hator or any other manufacturer.

Русская версия: [README.ru.md](README.ru.md)

## Idea

Laptop vendors ship control apps (performance modes, fans, lighting, charge limit) for Windows only. On Linux each laptop exposes a different set of interfaces. DOCKIT:

- scans the laptop on first run and shows which features are available;
- explains why a feature does not work and offers a fix, with your confirmation;
- keeps the logic (core) separate from the interface, so the same core can serve a window, a desktop-shell widget or the terminal;
- recognizes devices by hardware ID, using a plain-text device database that anyone can extend.

## Try it

```bash
git clone https://github.com/aktirf/dockit-panel
cd dockit-panel
python -m venv .venv && source .venv/bin/activate
pip install -e .
dockit scan      # what works on this laptop
dockit report    # text report to paste into a GitHub issue
```

The scan only **reads** system files. It does not change anything.

## Changing settings (background service)

Reading works without any setup. Changing a setting needs the small DOCKIT service, which runs as root and can do **only** the actions on a fixed list (switch the performance mode, switch the built-in camera on or off). Each change asks for your confirmation through the normal system password dialog (polkit).

```bash
sudo scripts/install-dev.sh      # install the service (copy goes to /opt/dockit, owned by root)
dockit profile                   # show the current performance mode
dockit profile performance       # change it (asks for confirmation)
dockit camera status|on|off      # built-in camera
sudo scripts/uninstall-dev.sh    # remove everything again
```

Safety: the service accepts only known actions, checks every value (a mode must be in the kernel's own list), never takes a file path from the client, and uses the caller's real process ID from the socket for the polkit check. The installed code in `/opt/dockit` is owned by root so a normal program cannot edit code that runs as root. These scripts are for testing; distribution packages come later.

## Profiles

A profile is a bundle of settings for a task: **Games** (performance), **Work** (balanced), **Night** (low-power).

```bash
dockit mode               # list profiles
dockit mode games         # switch to a profile (needs the service)
dockit auto               # switch profiles by itself using rules
```

Default rules: while a Steam game (`steam_app_*`) or `gamescope` runs, Games; on battery, Work. Your own profiles and rules go in `~/.config/dockit/profiles.toml`:

```toml
[profiles.games]
power = "performance"
camera = false            # optional: switch the camera off in this profile

[[rules]]
profile = "games"
processes = ["steam_app_*", "cs2"]

[[rules]]
profile = "night"
when = "battery"          # or "ac"
```

Rules are checked top to bottom, the first match wins. Mistakes in the file are ignored and the defaults are used.

## Sound

Works through PipeWire (the `pactl` command), no root needed.

```bash
dockit audio                   # outputs and microphones, * = in use now
dockit audio output epos       # send sound to the headset (part of the name is enough)
dockit audio input epos        # headset microphone
dockit audio mic mute|unmute   # mute or unmute the microphone
dockit audio volume 50         # volume of the current output, 0-150
```

A profile can include sound: `output = "epos"` and `input = "epos"` in `~/.config/dockit/profiles.toml`. If the device is missing (headset unplugged) the profile only reports it.

## Window

```bash
sudo pacman -S pyside6 ttf-ibm-plex     # the window (Qt) and the font used in the design
dockit gui
```

If you use a virtual environment, create it with access to system packages: `python -m venv --system-site-packages .venv`. The window reads data every 3 seconds and changes nothing by itself: modes, scenarios and the camera and microphone switches go through the background service. The Overview page is ready, the other sections are in progress.

## Automatic rules

On the Profiles page each profile can say when it switches on by itself (works with the "Auto" scenario on the Overview page):

- **A program is running**: pick from what is running now, or type a name (for example `cs2` or `steam_app_*`);
- **Power**: on battery or on the charger;
- **No activity** with keyboard and mouse for 5-60 minutes (needs `swayidle`: `sudo pacman -S swayidle`).

If several conditions are chosen, all of them must hold. Programs are checked first, then the rest. If no rule matches, the profile set under "If no rule matches" is used ("Work" by default). The chosen scenario ("Auto" and so on) is remembered between runs.

## Layout

| Folder | What it is |
|---|---|
| `src/dockit/core/` | statuses, base class for features, scanner |
| `src/dockit/modules/` | one file per feature |
| `src/dockit/cli/` | the `dockit` command |
| `devices/` | device database (one small file per device) |
| `docs/` | documentation |

## Help us support more laptops

Run `dockit report` and open an issue using the **Device report** template. Your report shows what works on your model and helps others.

## Planned

Background service (root actions with confirmation), profiles (games / work / night), peripherals (mouse, headset), window UI, AUR package.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Install

```
git clone https://github.com/aktirf/dockit-panel
cd dockit-panel
scripts/install.sh
```

Installs the packages DOCKIT needs, the service and an app-menu entry (Arch/EndeavourOS). Undo: `sudo scripts/uninstall-dev.sh`.
