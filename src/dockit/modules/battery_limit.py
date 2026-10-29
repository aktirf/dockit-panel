"""Battery charge limit (for example stop charging at 80%)."""

from __future__ import annotations

import glob

from ..core import sysfs
from ..core.module import Detection, Module
from ..core.status import Status

PATTERN = "/sys/class/power_supply/BAT*/charge_control_end_threshold"


def _paths() -> list[str]:
    return sorted(glob.glob(PATTERN))


class BatteryLimit(Module):
    id = "battery_limit"
    name = "Лимит заряда батареи"
    source = "power_supply"

    def detect(self) -> Detection:
        paths = _paths()
        if not paths:
            return Detection(
                Status.UNAVAILABLE,
                "Ядро не показывает лимит заряда для этой модели.",
            )
        if not all(sysfs.is_writable(p) for p in paths):
            return Detection(
                Status.NEEDS_SETUP,
                "Лимит виден, но нет прав на запись. Нужно правило udev.",
            )
        return Detection(Status.OK, "Лимит можно читать и менять.")

    def get_state(self):
        paths = _paths()
        if not paths:
            return None
        return sysfs.read_text(paths[0])

    def fix_hint(self) -> str:
        if not _paths():
            return "Обновите ядро или проверьте, поддерживает ли драйвер вашу модель."
        return "Добавьте правило udev, которое разрешает запись в этот файл."
