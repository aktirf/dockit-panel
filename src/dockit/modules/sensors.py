"""Temperatures and fan speeds from the kernel hwmon interface (read only)."""

from __future__ import annotations

import glob
import os

from ..core import sysfs
from ..core.module import Detection, Module
from ..core.status import Status

HWMON = "/sys/class/hwmon"


def _read_all(base: str | None = None) -> dict:
    hwmon_base = HWMON if base is None else base
    temps: dict[str, float] = {}
    fans: dict[str, int] = {}
    for hw in sorted(glob.glob(os.path.join(hwmon_base, "hwmon*"))):
        hw_id = os.path.basename(hw)
        chip = sysfs.read_text(os.path.join(hw, "name")) or hw_id
        for f in sorted(glob.glob(os.path.join(hw, "temp*_input"))):
            raw = sysfs.read_text(f)
            if raw and raw.lstrip("-").isdigit():
                key = f"{chip}/{os.path.basename(f)}"
                # Multiple chips can share a name (e.g. two NVMe SSDs or two DDR5 sticks): keep all.
                if key in temps:
                    key = f"{chip}/{hw_id}_{os.path.basename(f)}"
                temps[key] = int(raw) / 1000
        for f in sorted(glob.glob(os.path.join(hw, "fan*_input"))):
            raw = sysfs.read_text(f)
            if raw and raw.isdigit():
                key = f"{chip}/{os.path.basename(f)}"
                if key in fans:
                    key = f"{chip}/{hw_id}_{os.path.basename(f)}"
                fans[key] = int(raw)
    return {"temps_c": temps, "fans_rpm": fans}


class Sensors(Module):
    id = "sensors"
    name = "Температуры и вентиляторы"
    source = "hwmon"

    def __init__(self, base: str | None = None) -> None:
        self._base = base
        self._cache: dict | None = None

    def _read(self) -> dict:
        if self._cache is None:
            self._cache = _read_all(self._base)
        return self._cache

    def detect(self) -> Detection:
        data = self._read()
        if not data["temps_c"]:
            return Detection(Status.UNAVAILABLE, "Датчики температуры не найдены.")
        if not data["fans_rpm"]:
            return Detection(
                Status.OK,
                "Температуры видны. Обороты вентиляторов ядро не показывает.",
            )
        return Detection(Status.OK, "Температуры и обороты вентиляторов видны.")

    def get_state(self):
        return self._read()

    def fix_hint(self) -> str:
        return "Установите пакет lm_sensors и запустите sensors-detect."
