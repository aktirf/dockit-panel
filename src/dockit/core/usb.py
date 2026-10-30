"""List USB devices from /sys (read only, no serial numbers are read)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import sysfs

BASE = "/sys/bus/usb/devices"
LINUX_FOUNDATION = "1d6b"  # virtual root hubs, not real devices


@dataclass
class UsbDevice:
    usb_id: str        # "vendor:product" in lower case, e.g. "3277:00b2"
    manufacturer: str  # text the device reports about itself, may be empty
    product: str       # same
    port: str          # kernel name like "3-1"; needed to switch a device off


def list_usb(base: str | Path = BASE) -> list[UsbDevice]:
    devices = []
    root = Path(base)
    if not root.is_dir():
        return devices
    for entry in sorted(root.iterdir()):
        if ":" in entry.name:  # interface of a device, not a device
            continue
        vendor = sysfs.read_text(entry / "idVendor")
        product_id = sysfs.read_text(entry / "idProduct")
        if not vendor or not product_id:
            continue
        vendor = vendor.lower()
        if vendor == LINUX_FOUNDATION:
            continue
        devices.append(
            UsbDevice(
                usb_id=f"{vendor}:{product_id.lower()}",
                manufacturer=sysfs.read_text(entry / "manufacturer") or "",
                product=sysfs.read_text(entry / "product") or "",
                port=os.path.basename(entry),
            )
        )
    return devices
