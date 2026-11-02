"""Screen brightness and refresh rate.

Brightness is read from /sys/class/backlight (changing it is done by the root service).
Refresh rate is read and changed through the niri compositor (`niri msg`); other
compositors are not supported yet and simply report "unavailable".
"""

from __future__ import annotations

import glob
import json
import shutil
import subprocess

from . import sysfs

BACKLIGHT = "/sys/class/backlight"


def backlight_device(base: str = BACKLIGHT) -> str | None:
    best, best_max = None, 0
    for d in sorted(glob.glob(f"{base}/*")):
        raw = sysfs.read_text(f"{d}/max_brightness")
        if raw and raw.isdigit() and int(raw) > best_max:
            best, best_max = d, int(raw)
    return best


def brightness_percent(base: str = BACKLIGHT) -> int | None:
    dev = backlight_device(base)
    if dev is None:
        return None
    cur = sysfs.read_text(f"{dev}/brightness")
    top = sysfs.read_text(f"{dev}/max_brightness")
    if not (cur and top and cur.isdigit() and top.isdigit() and int(top) > 0):
        return None
    return round(100 * int(cur) / int(top))


def _niri_outputs() -> dict:
    tool = shutil.which("niri")
    if tool is None:
        return {}
    try:
        proc = subprocess.run([tool, "msg", "--json", "outputs"], capture_output=True, text=True, timeout=4)
        data = json.loads(proc.stdout) if proc.returncode == 0 else {}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _internal(outputs: dict):
    """(name, info) of the laptop's own screen (eDP...), or the first screen."""
    for name, info in outputs.items():
        if name.startswith(("eDP", "LVDS", "DSI")) and isinstance(info, dict):
            return name, info
    for name, info in outputs.items():
        if isinstance(info, dict):
            return name, info
    return None, None


def refresh_info(outputs: dict | None = None) -> dict:
    """{"output", "current", "rates": [Hz...]} for the built-in screen; rates are at the current resolution."""
    outputs = _niri_outputs() if outputs is None else outputs
    name, info = _internal(outputs)
    modes = (info or {}).get("modes") or []
    idx = (info or {}).get("current_mode")
    if not modes or not isinstance(idx, int) or not 0 <= idx < len(modes):
        return {"output": None, "current": None, "rates": []}
    cur = modes[idx]
    same = sorted({round(m["refresh_rate"] / 1000) for m in modes
                   if m.get("width") == cur.get("width") and m.get("height") == cur.get("height")})
    return {"output": name, "current": round(cur["refresh_rate"] / 1000), "rates": same}


def set_refresh(hz: int, outputs: dict | None = None) -> str | None:
    """Change the built-in screen to about `hz`. Returns an error text, or None if it worked."""
    outputs = _niri_outputs() if outputs is None else outputs
    name, info = _internal(outputs)
    modes = (info or {}).get("modes") or []
    idx = (info or {}).get("current_mode")
    if not modes or not isinstance(idx, int) or not 0 <= idx < len(modes):
        return "Частота экрана: поддерживается только в niri"
    cur = modes[idx]
    same = [m for m in modes if m.get("width") == cur.get("width") and m.get("height") == cur.get("height")]
    best = min(same, key=lambda m: abs(m["refresh_rate"] / 1000 - hz))
    spec = f"{best['width']}x{best['height']}@{best['refresh_rate'] / 1000:.3f}"
    try:
        proc = subprocess.run(["niri", "msg", "output", name, "mode", spec],
                              capture_output=True, text=True, timeout=6)
    except (OSError, subprocess.TimeoutExpired):
        return "Частота экрана: не удалось"
    return None if proc.returncode == 0 else "Частота экрана: не удалось"
