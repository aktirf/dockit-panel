"""Universal battery charge limit detection (sysfs threshold & Lenovo conservation_mode).

Pure read-only logic. Supports:
  * Standard Linux kernel `charge_control_end_threshold` (ThinkPad, ASUS, MSI, Dell,
    Samsung, Acer, Framework, System76, Huawei, etc.)
  * Lenovo IdeaPad / Legion `ideapad_acpi` `conservation_mode` (0 = 100%, 1 = ~80%)
"""

from __future__ import annotations

import glob

from . import sysfs

PS_BASE = "/sys/class/power_supply"
IDEAPAD_BASE = "/sys/bus/platform/drivers/ideapad_acpi"


def discover(ps_base: str = PS_BASE, ideapad_base: str = IDEAPAD_BASE) -> dict | None:
    """Return charge limit descriptor or None when the kernel does not expose one."""
    threshold_paths = [
        p for p in sorted(glob.glob(f"{ps_base}/*/charge_control_end_threshold"))
        if sysfs.read_text(p.rsplit("/", 1)[0] + "/scope") != "Device"
    ]
    if threshold_paths:
        raw = sysfs.read_text(threshold_paths[0])
        val = int(raw) if (raw and raw.isdigit()) else None
        return {
            "kind": "threshold",
            "paths": threshold_paths,
            "value": val,
            "conservation": None,
        }

    cons_paths = sorted(glob.glob(f"{ideapad_base}/VPC2004:*/conservation_mode"))
    if cons_paths:
        raw = sysfs.read_text(cons_paths[0])
        if raw in ("0", "1"):
            on = raw == "1"
            return {
                "kind": "conservation",
                "paths": cons_paths,
                "value": 80 if on else 100,
                "conservation": on,
            }

    return None
