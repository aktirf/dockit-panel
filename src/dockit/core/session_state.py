"""Persist and quietly restore runtime hardware choices across logins/reboots.

Compositor refresh rate (`hyprctl`, `niri`, `sway`, `xrandr`), ACPI platform
profile, and USB HID LampArray keyboard backlight reset when logging out or
rebooting. Saving them in `~/.config/dockit/session.json` lets DOCKIT restore
them silently (`interactive=False`, never prompting for a password) when the
window starts or when `dockit restore` runs on login.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from . import display, kbd_backlight, profiles, sysfs

PROFILE_PATH = "/sys/firmware/acpi/platform_profile"


def state_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "dockit" / "session.json"


def _validate_kbd(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    on = raw.get("on")
    autonomous = raw.get("autonomous", False)
    brightness = raw.get("brightness", 100)
    color = raw.get("color", "#5AB0FF")
    if not isinstance(on, bool) or not isinstance(autonomous, bool):
        return None
    if isinstance(brightness, bool) or not isinstance(brightness, int) or not 0 <= brightness <= 100:
        return None
    try:
        norm_color = kbd_backlight.normalize_hex_color(color)
    except ValueError:
        return None
    return {
        "on": on,
        "brightness": brightness,
        "color": norm_color,
        "autonomous": autonomous,
    }


def _clean(raw: dict) -> dict:
    out: dict = {}
    if not isinstance(raw, dict):
        return out
    refresh = raw.get("refresh")
    if isinstance(refresh, int) and not isinstance(refresh, bool) and 24 <= refresh <= 500:
        out["refresh"] = refresh
    power = raw.get("power")
    if isinstance(power, str) and power in (*profiles.POWER_VALUES, "dynamic"):
        out["power"] = power
    kbd = _validate_kbd(raw.get("kbd_backlight"))
    if kbd is not None:
        out["kbd_backlight"] = kbd
    return out


def load(path: Path | None = None) -> dict:
    p = path or state_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return _clean(data)


def has_saved(path: Path | None = None) -> bool:
    return bool(load(path))


def save(updates: dict, path: Path | None = None) -> dict:
    """Merge validated fields into session.json and write atomically."""
    p = path or state_path()
    current = load(p)
    cleaned = _clean(updates)
    current.update(cleaned)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        tmp.replace(p)
    except OSError:
        pass
    return current


def restore(
    ask_fn: Callable[[dict], dict | None],
    *,
    path: Path | None = None,
    include_power_and_refresh: bool = True,
    refresh_info_fn=display.refresh_info,
    set_refresh_fn=display.set_refresh,
    current_power_fn: Callable[[], str | None] | None = None,
    discover_kbd_fn=kbd_backlight.discover,
) -> list[str]:
    """Quietly re-apply saved hardware settings without ever showing a password dialog."""
    saved = load(path)
    if not saved:
        return []

    applied: list[str] = []

    if include_power_and_refresh:
        power = saved.get("power")
        if power:
            if current_power_fn:
                cur_power = current_power_fn()
            else:
                from . import tuning
                raw_power = sysfs.read_text(PROFILE_PATH)
                cur_power = "dynamic" if (raw_power == "balanced" and tuning.read_epp() == "dynamic") else raw_power
            if cur_power != power:
                res = ask_fn({"action": "set_power_profile", "value": power, "interactive": False})
                if res is not None:
                    applied.append(f"power={power}")

        hz = saved.get("refresh")
        if isinstance(hz, int):
            info = refresh_info_fn() or {}
            rates = info.get("rates") or []
            cur_hz = info.get("current")
            if hz in rates and cur_hz != hz:
                err = set_refresh_fn(hz)
                if err is None:
                    applied.append(f"refresh={hz}Hz")

    kbd = saved.get("kbd_backlight")
    if isinstance(kbd, dict) and discover_kbd_fn():
        res = ask_fn({"action": "set_kbd_backlight", "value": kbd, "interactive": False})
        if res is not None:
            applied.append("kbd_backlight")

    return applied
