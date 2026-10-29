"""Temperatures and fan speeds from the kernel hwmon interface (read only)."""

from __future__ import annotations

import glob
import os

from ..core import sysfs
from ..core.module import Detection, Module
from ..core.status import Status

HWMON = "/sys/class/hwmon"


def _read_all() -> dict:
    temps: dict[str, float] = {}
    fans: dict[str, int] = {}
    for hw in sorted(glob.glob(os.path.join(HWMON, "hwmon*"))):
        chip = sysfs.read_text(os.path.join(hw, "name")) or os.path.basename(hw)
        for f in sorted(glob.glob(os.path.join(hw, "temp*_input"))):
            raw = sysfs.read_text(f)
            if raw and raw.lstrip("-").isdigit():
                temps[f"{chip}/{os.path.basename(f)}"] = int(raw) / 1000
        for f in sorted(glob.glob(os.path.join(hw, "fan*_input"))):
            raw = sysfs.read_text(f)
            if raw and raw.isdigit():
                fans[f"{chip}/{os.path.basename(f)}"] = int(raw)
    return {"temps_c": temps, "fans_rpm": fans}


class Sensors(Module):
    id = "sensors"
    name = "Температуры и вентиляторы"
    source = "hwmon"

    def detect(self) -> Detection:
        data = _read_all()
        if not data["temps_c"]:
            return Detection(Status.UNAVAILABLE, "Датчики температуры не найдены.")
        if not data["fans_rpm"]:
            return Detection(
                Status.OK,
                "Температуры видны. Обороты вентиляторов ядро не показывает.",
            )
        return Detection(Status.OK, "Температуры и обороты вентиляторов видны.")

    def get_state(self):
        return _read_all()

    def fix_hint(self) -> str:
        return "Установите пакет lm_sensors и запустите sensors-detect."
