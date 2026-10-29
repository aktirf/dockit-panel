"""Performance mode (quiet / balanced / performance) via the kernel platform profile."""

from __future__ import annotations

from ..core import sysfs
from ..core.module import Detection, Module
from ..core.status import Status

PROFILE = "/sys/firmware/acpi/platform_profile"
CHOICES = "/sys/firmware/acpi/platform_profile_choices"


class PowerProfile(Module):
    id = "power_profile"
    name = "Режим производительности"
    source = "platform_profile"

    def detect(self) -> Detection:
        if not sysfs.exists(PROFILE):
            return Detection(
                Status.UNAVAILABLE,
                "Ядро не показывает режимы производительности для этой модели.",
            )
        if not sysfs.is_writable(PROFILE):
            return Detection(
                Status.NEEDS_SETUP,
                "Режим можно читать, но менять без прав администратора нельзя.",
            )
        return Detection(Status.OK, "Режим можно читать и менять.")

    def get_state(self):
        return {
            "current": sysfs.read_text(PROFILE),
            "choices": (sysfs.read_text(CHOICES) or "").split(),
        }

    def fix_hint(self) -> str:
        if not sysfs.exists(PROFILE):
            return (
                "Попробуйте более новое ядро. Запасной вариант: power-profiles-daemon "
                "и ryzenadj (лимиты мощности процессора)."
            )
        return "Нужно правило udev или фоновая служба DOCKIT, которая работает от root."
