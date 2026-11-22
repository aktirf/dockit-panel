"""Battery charge limit (standard charge_control_end_threshold & Lenovo conservation_mode)."""

from __future__ import annotations

from ..core import battery_limit as bl
from ..core import sysfs
from ..core.module import Detection, Module
from ..core.status import Status
from ..daemon.client import daemon_running


class BatteryLimit(Module):
    id = "battery_limit"
    name = "Лимит заряда батареи"
    source = "power_supply"

    def __init__(self, ps_base: str = bl.PS_BASE, ideapad_base: str = bl.IDEAPAD_BASE) -> None:
        self._ps = ps_base
        self._ideapad = ideapad_base

    def _info(self) -> dict | None:
        return bl.discover(self._ps, self._ideapad)

    def detect(self) -> Detection:
        info = self._info()
        if info is None:
            return Detection(
                Status.UNAVAILABLE,
                "Ядро не показывает лимит заряда для этой модели.",
            )
        writable = all(sysfs.is_writable(p) for p in info["paths"])
        if not writable and not daemon_running():
            return Detection(
                Status.NEEDS_SETUP,
                "Лимит виден, но для изменения нужна служба DOCKIT (или правило udev).",
            )
        val = info.get("value")
        if info["kind"] == "conservation":
            state_txt = "включён (80 %)" if info.get("conservation") else "выключен (100 %)"
            return Detection(Status.OK, f"Режим сбережения батареи: {state_txt}.")
        if val is not None:
            return Detection(Status.OK, f"Лимит заряда: {val} % (можно менять).")
        return Detection(Status.OK, "Лимит можно читать и менять.")

    def get_state(self):
        info = self._info()
        if info is None:
            return None
        return {
            "kind": info["kind"],
            "value": info["value"],
            "conservation": info["conservation"],
        }

    def fix_hint(self) -> str:
        if self._info() is None:
            return "Обновите ядро или проверьте, поддерживает ли драйвер вашу модель."
        return "Установите и запустите службу DOCKIT: sudo scripts/install-dev.sh."
