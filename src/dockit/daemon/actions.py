"""The only things the root service is allowed to change.

Every action checks its input strictly. The client never sends a file path:
the service decides which files to touch.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..core import sysfs
from ..core.usb import BASE as USB_BASE
from ..core.usb import list_usb
from ..peripherals.database import DeviceEntry, load_database

PROFILE = "/sys/firmware/acpi/platform_profile"
CHOICES = "/sys/firmware/acpi/platform_profile_choices"

# kernel names of USB ports look like "3-1" or "1-2.4"
PORT_RE = re.compile(r"^[0-9]+-[0-9]+(\.[0-9]+)*$")


class ActionError(Exception):
    """A request was refused. The message is safe to show to the user."""


def set_power_profile(value, profile_path: str = PROFILE, choices_path: str = CHOICES) -> dict:
    if not isinstance(value, str):
        raise ActionError("Режим должен быть строкой.")
    choices = (sysfs.read_text(choices_path) or "").split()
    if not choices:
        raise ActionError("Эта модель не поддерживает смену режима мощности.")
    if value not in choices:
        raise ActionError(f"Недопустимый режим. Доступно: {', '.join(choices)}.")
    try:
        Path(profile_path).write_text(value, encoding="ascii")
    except OSError as exc:
        raise ActionError(f"Не удалось записать режим: {exc.strerror or 'ошибка'}.") from exc
    return {"profile": sysfs.read_text(profile_path)}


def _camera_devices(usb_base: str, entries: list[DeviceEntry] | None):
    """Connected USB devices that the database says are cameras."""
    if entries is None:
        entries = load_database()
    camera_ids = set()
    for entry in entries:
        if entry.kind == "camera":
            camera_ids.update(i for i in [entry.usb_id, *entry.usb_ids] if i)
    return [d for d in list_usb(usb_base) if d.usb_id in camera_ids]


def camera_state(usb_base: str = USB_BASE, entries: list[DeviceEntry] | None = None) -> dict:
    cameras = []
    for dev in _camera_devices(usb_base, entries):
        raw = sysfs.read_text(Path(usb_base) / dev.port / "authorized")
        cameras.append({"usb_id": dev.usb_id, "port": dev.port, "enabled": raw == "1"})
    return {"cameras": cameras}


def set_camera(enabled, usb_base: str = USB_BASE, entries: list[DeviceEntry] | None = None) -> dict:
    if not isinstance(enabled, bool):
        raise ActionError("Значение должно быть true или false.")
    devices = _camera_devices(usb_base, entries)
    if not devices:
        raise ActionError("Камера не найдена в базе устройств.")
    for dev in devices:
        if not PORT_RE.match(dev.port):
            raise ActionError("Неожиданное имя USB-порта.")
        try:
            (Path(usb_base) / dev.port / "authorized").write_text(
                "1" if enabled else "0", encoding="ascii"
            )
        except OSError as exc:
            raise ActionError(f"Не удалось переключить камеру: {exc.strerror or 'ошибка'}.") from exc
    return camera_state(usb_base, entries)
