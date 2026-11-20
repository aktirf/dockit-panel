"""Connected Bluetooth devices and their battery level (read only, via bluetoothctl)."""

from __future__ import annotations

import re
import shutil
import subprocess


def _run(args: list[str]) -> str:
    try:
        proc = subprocess.run(["bluetoothctl", *args], capture_output=True, text=True, timeout=4)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout if proc.returncode == 0 else ""


def parse_powered(text: str) -> bool | None:
    """Whether the default Bluetooth adapter is powered on, from `bluetoothctl show`."""
    match = re.search(r"^\s*Powered:\s*(yes|no)\b", text, re.M | re.I)
    if not match:
        return None
    return match.group(1).lower() == "yes"


def adapter_powered() -> bool | None:
    """True/False from BlueZ (`bluetoothctl show`), or None if unavailable."""
    if shutil.which("bluetoothctl") is None:
        return None
    out = _run(["show"])
    return parse_powered(out) if out else None


def parse_info(text: str) -> dict:
    """Name and battery from the text of `bluetoothctl info`."""
    name = re.search(r"^\s*Name: (.+)$", text, re.M)
    battery = re.search(r"Battery Percentage: 0x[0-9a-fA-F]+ \((\d+)\)", text)
    icon = re.search(r"^\s*Icon: (\S+)", text, re.M)
    return {"name": name.group(1).strip() if name else "",
            "battery": int(battery.group(1)) if battery else None,
            "icon": icon.group(1) if icon else ""}


def connected_devices() -> list[dict]:
    if shutil.which("bluetoothctl") is None:
        return []
    result = []
    for line in _run(["devices", "Connected"]).splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) >= 2 and parts[0] == "Device" and re.fullmatch(r"[0-9A-Fa-f:]{17}", parts[1]):
            info = parse_info(_run(["info", parts[1]]))
            info["name"] = info["name"] or (parts[2] if len(parts) > 2 else parts[1])
            result.append(info)
    return result
