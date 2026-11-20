"""Keyboard (and LampArray peripheral) backlight discovery and control.

Supports two standard Linux mechanisms with zero external dependencies:
  1. USB HID LampArray (Usage Page 0x59, Lighting and Illumination — the open
     USB-IF standard used by Gigabyte Gaming A16 and Windows Dynamic Lighting
     devices) via /dev/hidraw* HIDIOCGFEATURE / HIDIOCSFEATURE ioctls.
  2. Standard kernel LED devices under /sys/class/leds/*kbd_backlight*.

Discovery functions only READ sysfs and never need root. Writing happens only
through the root daemon (dockit.daemon.actions.set_kbd_backlight).
"""

from __future__ import annotations

import fcntl
import os
import re
import struct
from dataclasses import dataclass
from pathlib import Path

from . import sysfs

HID_BASE = "/sys/bus/hid/devices"
LEDS_BASE = "/sys/class/leds"
DEV_BASE = "/dev"

HIDRAW_RE = re.compile(r"^hidraw[0-9]+$")
HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{6})$")
LED_NAME_RE = re.compile(r"^[A-Za-z0-9._:@-]+$")

# USB HID LampArray Usage Page (0x59) usages (USB-IF HUT 1.3+)
USAGE_PAGE_LIGHTING = 0x59
USAGE_LAMP_ARRAY = 0x01
USAGE_ATTRIBUTES_REPORT = 0x02
USAGE_RANGE_UPDATE_REPORT = 0x60
USAGE_CONTROL_REPORT = 0x70

# Linux <linux/hidraw.h>: _IOWR('H', 0x06 / 0x07, length)
_IOC_WRITE_READ = 3


def _hidioc_sfeature(length: int) -> int:
    return (_IOC_WRITE_READ << 30) | (length << 16) | (ord("H") << 8) | 0x06


def _hidioc_gfeature(length: int) -> int:
    return (_IOC_WRITE_READ << 30) | (length << 16) | (ord("H") << 8) | 0x07


@dataclass(frozen=True)
class LampArrayDevice:
    id: str              # sysfs device name, e.g. "0003:0414:8104.000A"
    name: str            # HID_NAME, e.g. "GIGABYTE USB-HID Keyboard"
    usb_id: str          # "0414:8104"
    hidraw: str          # validated basename, e.g. "hidraw9"
    attributes_id: int   # Report ID for LampArrayAttributesReport (usually 1)
    range_update_id: int # Report ID for LampRangeUpdateReport (usually 5)
    control_id: int      # Report ID for LampArrayControlReport (usually 6)


@dataclass(frozen=True)
class LedDevice:
    id: str              # directory name under /sys/class/leds
    name: str
    brightness: int
    max_brightness: int

    @property
    def percent(self) -> int:
        if self.max_brightness <= 0:
            return 0
        return max(0, min(100, round(100 * self.brightness / self.max_brightness)))


def parse_hex_color(value: str) -> tuple[int, int, int]:
    """Validate #RRGGBB and return (r, g, b) ints in 0..255."""
    if not isinstance(value, str):
        raise ValueError("color must be a #RRGGBB string")
    match = HEX_COLOR_RE.match(value.strip())
    if not match:
        raise ValueError("color must be a #RRGGBB string")
    hex_str = match.group(1)
    return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)


def normalize_hex_color(value: str) -> str:
    r, g, b = parse_hex_color(value)
    return f"#{r:02X}{g:02X}{b:02X}"


def parse_hid_uevent(text: str) -> dict[str, str]:
    """Extract HID_NAME and lowercase vid:pid from a HID sysfs uevent file."""
    name = ""
    usb_id = ""
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.strip()
        if key == "HID_NAME":
            name = val
        elif key == "HID_ID":
            # Format: BUS:VID:PID (e.g. 0003:00000414:00008104)
            parts = val.split(":")
            if len(parts) == 3:
                try:
                    vid = int(parts[1], 16) & 0xFFFF
                    pid = int(parts[2], 16) & 0xFFFF
                    usb_id = f"{vid:04x}:{pid:04x}"
                except ValueError:
                    pass
    return {"name": name, "usb_id": usb_id}


def parse_lamparray_descriptor(data: bytes) -> dict[str, int] | None:
    """Parse a raw USB HID report descriptor and return LampArray Report IDs if supported."""
    if not data:
        return None
    i = 0
    n = len(data)
    usage_page = 0
    report_id: int | None = None
    local_usages: list[int] = []
    is_lamparray = False
    ids: dict[str, int] = {}

    while i < n:
        b0 = data[i]
        if b0 == 0xFE:  # HID long item
            if i + 1 >= n:
                break
            i += 3 + data[i + 1]
            continue
        size_code = b0 & 0x03
        size = 4 if size_code == 3 else size_code
        if i + 1 + size > n:
            break
        item_type = (b0 >> 2) & 0x03
        item_tag = (b0 >> 4) & 0x0F
        val = int.from_bytes(data[i + 1 : i + 1 + size], "little") if size else 0
        i += 1 + size

        if item_type == 1:  # Global
            if item_tag == 0:  # Usage Page
                usage_page = val
            elif item_tag == 8:  # Report ID
                report_id = val
        elif item_type == 2:  # Local
            if item_tag == 0:  # Usage
                local_usages.append(val)
        elif item_type == 0:  # Main
            if usage_page == USAGE_PAGE_LIGHTING:
                if item_tag == 10 and val == 0x01 and USAGE_LAMP_ARRAY in local_usages:
                    is_lamparray = True
                if report_id is not None and item_tag in (10, 11):  # Collection or Feature
                    if USAGE_ATTRIBUTES_REPORT in local_usages:
                        ids.setdefault("attributes_id", report_id)
                    if USAGE_RANGE_UPDATE_REPORT in local_usages:
                        ids.setdefault("range_update_id", report_id)
                    if USAGE_CONTROL_REPORT in local_usages:
                        ids.setdefault("control_id", report_id)
            local_usages.clear()

    if not is_lamparray or "range_update_id" not in ids:
        return None
    return {
        "attributes_id": ids.get("attributes_id", 1),
        "range_update_id": ids["range_update_id"],
        "control_id": ids.get("control_id", 6),
    }


def parse_attributes_report(data: bytes) -> dict[str, int] | None:
    """Decode a 23-byte LampArrayAttributesReport (Report ID 1)."""
    if len(data) < 3:
        return None
    if len(data) >= 23:
        rid, count, w, h, d, kind, min_us = struct.unpack("<BHIIIII", data[:23])
        return {
            "report_id": rid,
            "lamp_count": count,
            "width_um": w,
            "height_um": h,
            "depth_um": d,
            "kind": kind,
            "min_update_us": min_us,
        }
    rid, count = struct.unpack("<BH", data[:3])
    return {"report_id": rid, "lamp_count": count}


def build_control_report(autonomous: bool, report_id: int = 6) -> bytes:
    """Build a 2-byte LampArrayControlReport (autonomous=True returns control to firmware/Fn)."""
    return struct.pack("<BB", report_id & 0xFF, 1 if autonomous else 0)


def scale_led_rgb(
    r: int,
    g: int,
    b: int,
    brightness: int,
    gamma: float = 2.2,
    brightness_gamma: float = 1.6,
) -> tuple[int, int, int]:
    """Convert sRGB (0..255) + perceptual brightness (0..100) to linear LED PWM values.

    Without sRGB gamma correction, linear RGB keyboard LEDs over-brighten secondary
    sub-channels (e.g., green #22C55E looks cyan because B=94 is 37% linear power).
    """
    brightness = max(0, min(100, int(brightness)))
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))

    if brightness <= 0 or (r == 0 and g == 0 and b == 0):
        return 0, 0, 0

    b_scale = (brightness / 100.0) ** brightness_gamma
    sr = round(255 * ((r / 255.0) ** gamma) * b_scale)
    sg = round(255 * ((g / 255.0) ** gamma) * b_scale)
    sb = round(255 * ((b / 255.0) ** gamma) * b_scale)

    # Keep non-black colors faintly visible at 1% instead of rounding down to 0.
    if sr == 0 and sg == 0 and sb == 0:
        peak = max(r, g, b)
        sr = 1 if r == peak else 0
        sg = 1 if g == peak else 0
        sb = 1 if b == peak else 0
    return sr, sg, sb


def build_range_update_report(
    lamp_count: int,
    r: int,
    g: int,
    b: int,
    brightness: int,
    report_id: int = 5,
) -> bytes:
    """Build a 10-byte LampRangeUpdateReport setting all lamps to one gamma-corrected RGB color.

    RGB channels are scaled by brightness (0..100) because many laptop LampArray
    firmwares (including Gigabyte Gaming A16) treat the intensity byte as on/off.
    """
    sr, sg, sb = scale_led_rgb(r, g, b, brightness)
    intensity = 255 if (sr or sg or sb) else 0
    end_id = max(0, min(0xFFFF, int(lamp_count) - 1))
    flags = 0x01  # LAMP_UPDATE_COMPLETE
    return struct.pack("<BBHHBBBB", report_id & 0xFF, flags, 0, end_id, sr, sg, sb, intensity)


def _subdirs(base: str | Path) -> list[Path]:
    try:
        return sorted(p for p in Path(base).iterdir() if p.is_dir())
    except OSError:
        return []


def _read_int(path: str | Path) -> int | None:
    text = sysfs.read_text(path)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def discover_lamparray(hid_base: str = HID_BASE) -> list[LampArrayDevice]:
    """Find all connected USB HID LampArray devices (read-only sysfs scan)."""
    devices: list[LampArrayDevice] = []
    for dev_dir in _subdirs(hid_base):
        desc_path = dev_dir / "report_descriptor"
        try:
            desc = desc_path.read_bytes()
        except OSError:
            continue
        ids = parse_lamparray_descriptor(desc)
        if ids is None:
            continue
        hidraw_dir = dev_dir / "hidraw"
        hidraw_name = ""
        for entry in _subdirs(hidraw_dir):
            if HIDRAW_RE.match(entry.name):
                hidraw_name = entry.name
                break
        if not hidraw_name:
            continue
        meta = parse_hid_uevent(sysfs.read_text(dev_dir / "uevent") or "")
        devices.append(
            LampArrayDevice(
                id=dev_dir.name,
                name=meta["name"] or dev_dir.name,
                usb_id=meta["usb_id"],
                hidraw=hidraw_name,
                attributes_id=ids["attributes_id"],
                range_update_id=ids["range_update_id"],
                control_id=ids["control_id"],
            )
        )
    return devices


def discover_leds(leds_base: str = LEDS_BASE) -> list[LedDevice]:
    """Find standard kernel keyboard backlight LEDs under /sys/class/leds."""
    devices: list[LedDevice] = []
    for led_dir in _subdirs(leds_base):
        if "kbd_backlight" not in led_dir.name:
            continue
        if not LED_NAME_RE.match(led_dir.name):
            continue
        cur = _read_int(led_dir / "brightness")
        top = _read_int(led_dir / "max_brightness")
        if cur is None or top is None or top <= 0:
            continue
        devices.append(LedDevice(id=led_dir.name, name=led_dir.name, brightness=cur, max_brightness=top))
    return devices


def discover(hid_base: str = HID_BASE, leds_base: str = LEDS_BASE) -> list[dict]:
    """Unified read-only list of supported keyboard/LampArray backlight devices."""
    out: list[dict] = []
    for dev in discover_lamparray(hid_base):
        out.append({
            "id": dev.id,
            "name": dev.name,
            "backend": "lamparray",
            "rgb": True,
            "usb_id": dev.usb_id,
            "brightness": None,
        })
    for led in discover_leds(leds_base):
        out.append({
            "id": led.id,
            "name": led.name,
            "backend": "led",
            "rgb": False,
            "usb_id": "",
            "brightness": led.percent,
        })
    return out


def _ioctl_feature(fd: int, request: int, buf: bytearray) -> bytearray:
    fcntl.ioctl(fd, request, buf, True)
    return buf


def apply_lamparray(
    dev: LampArrayDevice,
    *,
    on: bool,
    brightness: int,
    color: str = "#5AB0FF",
    autonomous: bool = False,
    dev_base: str = DEV_BASE,
    ioctl_fn=_ioctl_feature,
) -> dict:
    """Apply backlight state to one HID LampArray device (requires write access to /dev/hidraw*)."""
    if not HIDRAW_RE.match(dev.hidraw):
        raise ValueError("unexpected hidraw device name")
    r, g, b = parse_hex_color(color)
    norm_color = f"#{r:02X}{g:02X}{b:02X}"
    effective_brightness = max(0, min(100, int(brightness))) if on else 0
    dev_path = os.path.join(dev_base, dev.hidraw)

    fd = os.open(dev_path, os.O_RDWR)
    try:
        lamp_count = 1
        if not autonomous:
            attr_buf = bytearray(23)
            attr_buf[0] = dev.attributes_id & 0xFF
            try:
                ioctl_fn(fd, _hidioc_gfeature(len(attr_buf)), attr_buf)
                parsed = parse_attributes_report(bytes(attr_buf))
                if parsed and parsed["lamp_count"] > 0:
                    lamp_count = parsed["lamp_count"]
            except OSError:
                lamp_count = 1

        ctrl = bytearray(build_control_report(autonomous, dev.control_id))
        ioctl_fn(fd, _hidioc_sfeature(len(ctrl)), ctrl)

        if not autonomous:
            upd = bytearray(
                build_range_update_report(lamp_count, r, g, b, effective_brightness, dev.range_update_id)
            )
            ioctl_fn(fd, _hidioc_sfeature(len(upd)), upd)
    finally:
        os.close(fd)

    return {
        "device": dev.name,
        "backend": "lamparray",
        "rgb": True,
        "on": bool(on) and effective_brightness > 0 if not autonomous else True,
        "brightness": int(brightness),
        "color": norm_color,
        "autonomous": bool(autonomous),
        "lamps": lamp_count,
    }


def apply_led(
    dev: LedDevice,
    *,
    on: bool,
    brightness: int,
    leds_base: str = LEDS_BASE,
) -> dict:
    """Apply brightness to one standard /sys/class/leds/*kbd_backlight* device."""
    if not LED_NAME_RE.match(dev.id):
        raise ValueError("unexpected LED device name")
    pct = max(0, min(100, int(brightness))) if on else 0
    raw = 0 if pct == 0 else max(1, round(dev.max_brightness * pct / 100))
    Path(leds_base, dev.id, "brightness").write_text(str(raw), encoding="ascii")
    return {
        "device": dev.name,
        "backend": "led",
        "rgb": False,
        "on": raw > 0,
        "brightness": round(100 * raw / dev.max_brightness) if dev.max_brightness > 0 else 0,
        "color": "",
        "autonomous": False,
        "lamps": 1,
    }
