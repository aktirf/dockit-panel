"""Wi-Fi and Bluetooth switches (rfkill, read only here)."""

from __future__ import annotations

import glob
import os

from ..core import sysfs
from ..core.module import Detection, Module
from ..core.status import Status

RFKILL = "/sys/class/rfkill"


def _read_all() -> dict[str, bool]:
    """Return {'wlan': True/False, 'bluetooth': ...}; True means enabled."""
    result: dict[str, bool] = {}
    for d in sorted(glob.glob(os.path.join(RFKILL, "rfkill*"))):
        kind = sysfs.read_text(os.path.join(d, "type"))
        soft = sysfs.read_text(os.path.join(d, "soft"))
        hard = sysfs.read_text(os.path.join(d, "hard"))
        if kind in ("wlan", "bluetooth") and soft is not None:
            enabled = soft == "0" and hard in (None, "0")
            # several switches of one kind can exist (extra vendor ones): the radio is on if any is on
            result[kind] = result.get(kind, False) or enabled
    return result


class Wireless(Module):
    id = "wireless"
    name = "Wi-Fi и Bluetooth"
    source = "rfkill"

    def detect(self) -> Detection:
        data = _read_all()
        if not data:
            return Detection(Status.UNAVAILABLE, "Переключатели Wi-Fi и Bluetooth не найдены.")
        return Detection(Status.OK, "Модули найдены: " + ", ".join(data))

    def get_state(self):
        return _read_all()

    def fix_hint(self) -> str:
        return "Проверьте, что драйверы Wi-Fi и Bluetooth загружены (команда: rfkill list)."
