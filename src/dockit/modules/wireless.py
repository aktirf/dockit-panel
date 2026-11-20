"""Wi-Fi and Bluetooth switches (rfkill + BlueZ adapter power, read only here)."""

from __future__ import annotations

import glob
import os
from typing import Callable

from ..core import bluetooth, sysfs
from ..core.module import Detection, Module
from ..core.status import Status

RFKILL = "/sys/class/rfkill"


def _read_all(
    rfkill_base: str | None = None,
    bt_powered: Callable[[], bool | None] | None = None,
) -> dict[str, bool]:
    """Return {'wlan': True/False, 'bluetooth': ...}; True means enabled.

    `bluetoothctl power off` powers off the BlueZ adapter without setting an rfkill
    soft-block, so for Bluetooth we combine rfkill with `bluetoothctl show` ("Powered").
    """
    base = RFKILL if rfkill_base is None else rfkill_base
    result: dict[str, bool] = {}
    for d in sorted(glob.glob(os.path.join(base, "rfkill*"))):
        kind = sysfs.read_text(os.path.join(d, "type"))
        soft = sysfs.read_text(os.path.join(d, "soft"))
        hard = sysfs.read_text(os.path.join(d, "hard"))
        if kind in ("wlan", "bluetooth") and soft is not None:
            enabled = soft == "0" and hard in (None, "0")
            # several switches of one kind can exist (extra vendor ones): the radio is on if any is on
            result[kind] = result.get(kind, False) or enabled

    if result.get("bluetooth", True):
        # Only query BlueZ when rfkill has not already blocked Bluetooth (or when no rfkill node exists).
        powered = (bluetooth.adapter_powered if bt_powered is None else bt_powered)()
        if powered is not None:
            result["bluetooth"] = result.get("bluetooth", True) and powered
    return result


class Wireless(Module):
    id = "wireless"
    name = "Wi-Fi и Bluetooth"
    source = "rfkill"

    def __init__(
        self,
        rfkill_base: str | None = None,
        bt_powered: Callable[[], bool | None] | None = None,
    ) -> None:
        self._rfkill_base = rfkill_base
        self._bt_powered = bt_powered
        self._cache: dict[str, bool] | None = None

    def _read(self) -> dict[str, bool]:
        if self._cache is None:
            self._cache = _read_all(self._rfkill_base, self._bt_powered)
        return dict(self._cache)

    def detect(self) -> Detection:
        data = self._read()
        if not data:
            return Detection(Status.UNAVAILABLE, "Переключатели Wi-Fi и Bluetooth не найдены.")
        return Detection(Status.OK, "Модули найдены: " + ", ".join(data))

    def get_state(self):
        return self._read()

    def fix_hint(self) -> str:
        return "Проверьте, что драйверы Wi-Fi и Bluetooth загружены (команда: rfkill list)."
