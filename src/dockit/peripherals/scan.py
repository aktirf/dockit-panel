"""Find connected USB devices and match them against the device database."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.usb import UsbDevice, list_usb
from .database import DeviceEntry, find_by_usb, load_database

KIND_RU = {
    "laptop": "Ноутбук",
    "mouse": "Мышь",
    "headset": "Наушники",
    "camera": "Камера",
    "keyboard": "Клавиатура",
    "bluetooth": "Bluetooth",
    "unknown": "Неизвестно",
}


@dataclass
class PeripheralItem:
    usb_id: str
    name: str
    kind: str
    known: bool          # True if the device is in the database
    status: str
    features: list[str] = field(default_factory=list)
    notes: str = ""
    usb_name: str = ""   # what the device calls itself


def scan_peripherals(
    usb_devices: list[UsbDevice] | None = None,
    entries: list[DeviceEntry] | None = None,
) -> list[PeripheralItem]:
    if usb_devices is None:
        usb_devices = list_usb()
    if entries is None:
        entries = load_database()

    items = []
    for dev in usb_devices:
        usb_name = dev.product or dev.manufacturer
        entry = find_by_usb(entries, dev.usb_id)
        if entry:
            items.append(
                PeripheralItem(
                    usb_id=dev.usb_id, name=entry.name, kind=entry.kind, known=True,
                    status=entry.status, features=entry.features, notes=entry.notes,
                    usb_name=usb_name,
                )
            )
        else:
            items.append(
                PeripheralItem(
                    usb_id=dev.usb_id, name=usb_name or "Неизвестное устройство",
                    kind="unknown", known=False, status="unknown", usb_name=usb_name,
                )
            )
    items.sort(key=lambda i: (not i.known, i.usb_id))
    return items
