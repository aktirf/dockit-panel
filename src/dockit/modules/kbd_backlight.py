"""Keyboard (and HID LampArray) backlight detection (read only; changes go through the service)."""

from __future__ import annotations

from ..core import kbd_backlight
from ..core.module import Detection, Module
from ..core.status import Status
from ..daemon.client import daemon_running


class KbdBacklight(Module):
    id = "kbd_backlight"
    name = "Подсветка клавиатуры"
    source = "HID LampArray / sysfs leds"

    def detect(self) -> Detection:
        devices = kbd_backlight.discover()
        if not devices:
            return Detection(
                Status.UNAVAILABLE,
                "Подсветка не видна через HID LampArray или /sys/class/leds.",
            )
        names = ", ".join(d["name"] for d in devices)
        mode = "HID LampArray RGB" if any(d["rgb"] for d in devices) else "LED"
        if not daemon_running():
            return Detection(
                Status.NEEDS_SETUP,
                f"Найдена подсветка ({names}, {mode}), но для управления нужна служба DOCKIT.",
            )
        return Detection(Status.OK, f"{names} ({mode}).")

    def get_state(self):
        devices = kbd_backlight.discover()
        if not devices:
            return None
        return {
            "devices": devices,
            "available": True,
            "rgb": any(d["rgb"] for d in devices),
            "backend": devices[0]["backend"],
        }

    def fix_hint(self) -> str:
        if kbd_backlight.discover():
            return "Установите и запустите службу DOCKIT: sudo scripts/install-dev.sh."
        return "Управляется встроенной прошивкой клавиатуры."
