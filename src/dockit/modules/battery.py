"""Battery: charge level, state, wear (read only)."""

from __future__ import annotations

import glob
import os

from ..core import sysfs
from ..core.module import Detection, Module
from ..core.status import Status

BASE = "/sys/class/power_supply"

STATUS_RU = {
    "Charging": "заряжается",
    "Discharging": "работает от батареи",
    "Full": "полностью заряжена",
    "Not charging": "не заряжается",
}


def _int(path: str) -> int | None:
    raw = sysfs.read_text(path)
    return int(raw) if raw is not None and raw.lstrip("-").isdigit() else None


def read_batteries(base: str = BASE) -> list[dict]:
    result = []
    for d in sorted(glob.glob(os.path.join(base, "BAT*"))):
        full = _int(f"{d}/energy_full")
        design = _int(f"{d}/energy_full_design")
        if full is None or design is None:  # some batteries report charge, not energy
            full = _int(f"{d}/charge_full")
            design = _int(f"{d}/charge_full_design")
        health = round(full / design * 100, 1) if full and design else None
        result.append(
            {
                "name": os.path.basename(d),
                "percent": _int(f"{d}/capacity"),
                "status": sysfs.read_text(f"{d}/status"),
                "health_pct": health,
                "cycles": _int(f"{d}/cycle_count"),
            }
        )
    return result


def ac_online(base: str = BASE) -> bool | None:
    """True if a mains adapter is plugged in, None if there is no adapter info."""
    found = None
    for d in sorted(glob.glob(os.path.join(base, "*"))):
        if sysfs.read_text(f"{d}/type") == "Mains":
            online = sysfs.read_text(f"{d}/online")
            if online is not None:
                found = found or online == "1"
    return found


class Battery(Module):
    id = "battery"
    name = "Батарея"
    source = "power_supply"

    def detect(self) -> Detection:
        batteries = read_batteries()
        if not batteries:
            return Detection(
                Status.UNAVAILABLE,
                "Батарея не найдена (возможно, это настольный компьютер).",
            )
        b = batteries[0]
        if b["percent"] is None:
            return Detection(Status.UNAVAILABLE, "Заряд батареи не читается.")
        state = STATUS_RU.get(b["status"] or "", "состояние неизвестно")
        return Detection(Status.OK, f"Заряд {b['percent']} %, {state}.")

    def get_state(self):
        batteries = read_batteries()
        if not batteries:
            return None
        return {"batteries": batteries, "ac_online": ac_online()}

    def fix_hint(self) -> str:
        return ""
