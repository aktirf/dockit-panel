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
UNSUPPORTED = "Частота экрана: не поддерживается в этом окружении"
INTERNAL = ("eDP", "LVDS", "DSI")


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


def _hypr_monitors() -> list:
    tool = shutil.which("hyprctl")
    if tool is None:
        return []
    try:
        proc = subprocess.run([tool, "monitors", "-j"], capture_output=True, text=True, timeout=4)
        data = json.loads(proc.stdout) if proc.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return []
    return data if isinstance(data, list) else []


def _hypr_internal(monitors: list):
    for m in monitors:
        if isinstance(m, dict) and str(m.get("name", "")).startswith(("eDP", "LVDS", "DSI")):
            return m
    return next((m for m in monitors if isinstance(m, dict)), None)


def _hypr_rates(mon: dict) -> list[int]:
    """Refresh rates (Hz) offered at the current resolution; modes look like "2560x1600@165.00Hz"."""
    size = f"{mon.get('width')}x{mon.get('height')}"
    rates = set()
    for mode in mon.get("availableModes") or []:
        text = str(mode)
        if text.startswith(size + "@") and text.endswith("Hz"):
            try:
                rates.add(round(float(text[len(size) + 1:-2])))
            except ValueError:
                pass
    return sorted(rates)


def _niri_hypr_info(outputs: dict | None = None, monitors: list | None = None) -> dict:
    """{"output", "current", "rates": [Hz...]} for the built-in screen; rates are at the current resolution."""
    outputs = _niri_outputs() if outputs is None else outputs
    name, info = _internal(outputs)
    modes = (info or {}).get("modes") or []
    idx = (info or {}).get("current_mode")
    if not modes or not isinstance(idx, int) or not 0 <= idx < len(modes):
        mon = _hypr_internal(_hypr_monitors() if monitors is None else monitors)     # Hyprland
        if mon and mon.get("refreshRate"):
            return {"output": mon.get("name"), "current": round(float(mon["refreshRate"])),
                    "rates": _hypr_rates(mon)}
        return {"output": None, "current": None, "rates": []}
    cur = modes[idx]
    same = sorted({round(m["refresh_rate"] / 1000) for m in modes
                   if m.get("width") == cur.get("width") and m.get("height") == cur.get("height")})
    return {"output": name, "current": round(cur["refresh_rate"] / 1000), "rates": same}


def _niri_hypr_set(hz: int, outputs: dict | None = None, monitors: list | None = None) -> str | None:
    """Change the built-in screen to about `hz`. Returns an error text, or None if it worked."""
    outputs = _niri_outputs() if outputs is None else outputs
    name, info = _internal(outputs)
    modes = (info or {}).get("modes") or []
    idx = (info or {}).get("current_mode")
    if not modes or not isinstance(idx, int) or not 0 <= idx < len(modes):
        mon = _hypr_internal(_hypr_monitors() if monitors is None else monitors)     # Hyprland
        rates = _hypr_rates(mon) if mon else []
        if not rates:
            return UNSUPPORTED
        best = min(rates, key=lambda r: abs(r - hz))
        spec = (f"{mon['name']},{mon['width']}x{mon['height']}@{best},"
                f"{mon.get('x', 0)}x{mon.get('y', 0)},{mon.get('scale', 1)}")
        try:
            proc = subprocess.run(["hyprctl", "keyword", "monitor", spec],
                                  capture_output=True, text=True, timeout=6)
        except (OSError, subprocess.TimeoutExpired):
            return "Частота экрана: не удалось"
        return None if proc.returncode == 0 and "ok" in proc.stdout.lower() else "Частота экрана: не удалось"
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


# ---------- Sway and other wlroots compositors ----------

def _run(args: list[str], timeout: int = 5) -> str | None:
    if shutil.which(args[0]) is None:
        return None
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _pick(items: list, name_of):
    """The laptop's own screen if there is one, otherwise the first screen."""
    for it in items:
        if str(name_of(it)).startswith(INTERNAL):
            return it
    return items[0] if items else None


def parse_sway(text: str) -> dict:
    try:
        data = json.loads(text)
    except ValueError:
        return {"output": None, "current": None, "rates": [], "modes": []}
    outs = [o for o in data if isinstance(o, dict) and o.get("active", True) and o.get("current_mode")] \
        if isinstance(data, list) else []
    out = _pick(outs, lambda o: o.get("name", ""))
    if not out:
        return {"output": None, "current": None, "rates": [], "modes": []}
    cur = out["current_mode"]
    rates = sorted({round(m["refresh"] / 1000) for m in out.get("modes", [])
                    if m.get("width") == cur.get("width") and m.get("height") == cur.get("height")})
    return {"output": out["name"], "current": round(cur["refresh"] / 1000), "rates": rates,
            "size": f"{cur['width']}x{cur['height']}"}


def _sway_info() -> dict:
    text = _run(["swaymsg", "-t", "get_outputs", "-r"])
    return parse_sway(text) if text else {"output": None, "current": None, "rates": []}


def _sway_set(hz: int) -> str | None:
    info = _sway_info()
    if not info["rates"]:
        return UNSUPPORTED
    best = min(info["rates"], key=lambda r: abs(r - hz))
    ok = _run(["swaymsg", "output", info["output"], "mode", f"{info['size']}@{best}Hz"])
    return None if ok is not None else "Частота экрана: не удалось"


# ---------- KDE Plasma ----------

def parse_kscreen(text: str) -> dict:
    try:
        data = json.loads(text)
    except ValueError:
        return {"output": None, "current": None, "rates": [], "modes": {}}
    outs = [o for o in (data.get("outputs") or []) if isinstance(o, dict) and o.get("enabled")] \
        if isinstance(data, dict) else []
    out = _pick(outs, lambda o: o.get("name", ""))
    if not out:
        return {"output": None, "current": None, "rates": [], "modes": {}}
    modes = out.get("modes") or []
    cur = next((m for m in modes if m.get("id") == out.get("currentModeId")), None)
    if not cur:
        return {"output": None, "current": None, "rates": [], "modes": {}}
    size = cur.get("size", {})
    same = {}
    for m in modes:
        if m.get("size") == size:
            same[round(m["refreshRate"])] = m["id"]
    return {"output": out["name"], "current": round(cur["refreshRate"]), "rates": sorted(same), "modes": same}


def _kde_info() -> dict:
    text = _run(["kscreen-doctor", "-j"])
    return parse_kscreen(text) if text else {"output": None, "current": None, "rates": [], "modes": {}}


def _kde_set(hz: int) -> str | None:
    info = _kde_info()
    if not info["rates"]:
        return UNSUPPORTED
    best = min(info["rates"], key=lambda r: abs(r - hz))
    ok = _run(["kscreen-doctor", f"output.{info['output']}.mode.{info['modes'][best]}"])
    return None if ok is not None else "Частота экрана: не удалось"


# ---------- X11 ----------

def parse_xrandr(text: str) -> dict:
    """Parse `xrandr --query`; the active mode is marked with * after its rate."""
    name, size, current, rates = None, None, None, []
    blocks = []
    cur_block = None
    for line in text.splitlines():
        if line and not line[0].isspace():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "connected":
                cur_block = {"name": parts[0], "modes": []}
                blocks.append(cur_block)
            else:
                cur_block = None
        elif cur_block is not None and line.strip():
            fields = line.split()
            cur_block["modes"].append((fields[0], fields[1:]))
    block = _pick([b for b in blocks if any("*" in r for _, rs in b["modes"] for r in rs)],
                  lambda b: b["name"])
    if not block:
        return {"output": None, "current": None, "rates": []}
    for mode, rs in block["modes"]:
        if any("*" in r for r in rs):
            size = mode
            current = next((round(float(r.strip("*+"))) for r in rs if "*" in r), None)
            break
    for mode, rs in block["modes"]:
        if mode == size:
            for r in rs:
                try:
                    rates.append(round(float(r.strip("*+"))))
                except ValueError:
                    pass
    return {"output": block["name"], "current": current, "rates": sorted(set(rates)), "size": size}


def _x11_info() -> dict:
    text = _run(["xrandr", "--query"])
    return parse_xrandr(text) if text else {"output": None, "current": None, "rates": []}


def _x11_set(hz: int) -> str | None:
    info = _x11_info()
    if not info["rates"]:
        return UNSUPPORTED
    best = min(info["rates"], key=lambda r: abs(r - hz))
    ok = _run(["xrandr", "--output", info["output"], "--mode", info["size"], "--rate", str(best)])
    return None if ok is not None else "Частота экрана: не удалось"


# ---------- choose the right one ----------

_OTHERS = (("sway", _sway_info, _sway_set), ("kde", _kde_info, _kde_set), ("x11", _x11_info, _x11_set))


def refresh_info(outputs: dict | None = None, monitors: list | None = None) -> dict:
    """{"output", "current", "rates": [Hz...]} for the built-in screen, whatever the desktop is."""
    info = _niri_hypr_info(outputs, monitors)
    if info["output"] is not None or outputs is not None or monitors is not None:
        return info
    for _, find, _ in _OTHERS:
        info = find()
        if info.get("output"):
            return {"output": info["output"], "current": info["current"], "rates": info["rates"]}
    return {"output": None, "current": None, "rates": []}


def set_refresh(hz: int, outputs: dict | None = None, monitors: list | None = None) -> str | None:
    """Change the built-in screen to about `hz`. Returns an error text, or None if it worked."""
    error = _niri_hypr_set(hz, outputs, monitors)
    if error != UNSUPPORTED or outputs is not None or monitors is not None:
        return error
    for _, find, apply in _OTHERS:
        if find().get("output"):
            return apply(hz)
    return UNSUPPORTED
