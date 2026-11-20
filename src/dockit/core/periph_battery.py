"""Peripheral battery discovery (read only, zero external runtime dependencies).

Collects battery levels of wireless mice, keyboards, headsets, gamepads,
tablets and Bluetooth peripherals from standard Linux sources:
  1. /sys/class/power_supply/* entries with scope=Device (kernel HID++,
     hid-sony, hid-nintendo, wacom, xpad, etc.);
  2. UPower (`upower -d`) for non-system peripheral batteries (including
     BlueZ / HOGP / HFP devices exposed through UPower);
  3. Optional `headsetcontrol` CLI (if installed) for gaming USB headsets.

Every parser is a pure function so it can be unit-tested with sample text.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import sysfs

POWER_SUPPLY = "/sys/class/power_supply"

# Normalized status strings: "charging", "discharging", "full", "unknown"
_STATUS_MAP = {
    "charging": "charging",
    "pending-charge": "charging",
    "discharging": "discharging",
    "pending-discharge": "discharging",
    "full": "full",
    "fully-charged": "full",
    "not charging": "full",
    "empty": "discharging",
    "unknown": "unknown",
}

_LAPTOP_BAT_RE = re.compile(r"^(BAT\d*|BATT|CMB\d*|AC\d*|ACAD|ADP\d*|ucsi-source-psy.*)$", re.I)
_MAC_RE = re.compile(r"([0-9a-fA-F]{2}[:_-]){5}[0-9a-fA-F]{2}")

# UPower device paths that represent peripherals rather than laptop main batteries
_UPOWER_PERIPH_PREFIXES = (
    "mouse_",
    "keyboard_",
    "gaming_input_",
    "headset_",
    "headphones_",
    "speakers_",
    "audio_device_",
    "tablet_",
    "media_player_",
    "pen_",
    "touchpad_",
    "bluetooth_generic_",
)


@dataclass(frozen=True)
class PeripheralBattery:
    name: str
    percent: int | None          # 0..100, or None if only coarse level is known
    status: str = "unknown"      # charging | discharging | full | unknown
    kind: str = "device"         # mouse | keyboard | headset | gamepad | tablet | device
    source: str = "sysfs"        # sysfs | upower | headsetcontrol | bluetooth
    key: str = ""                # native path / serial / MAC for deduplication
    level: str = ""              # optional coarse level (High/Normal/Low) when percent is None


def _norm_status(raw: str) -> str:
    return _STATUS_MAP.get(raw.strip().lower(), "unknown")


def _norm_key(text: str) -> str:
    """Normalize a serial or MAC address for deduplication across sources."""
    m = _MAC_RE.search(text)
    if m:
        return re.sub(r"[:_-]", "", m.group(0)).lower()
    cleaned = re.sub(r"[^a-z0-9]+", "", text.lower())
    return cleaned


def _guess_kind(name: str, hint: str = "") -> str:
    blob = f"{name} {hint}".lower()
    if any(w in blob for w in ("mouse", "mice", "trackball", "mx master", "g pro", "deathadder", "viper", "stellar")):
        return "mouse"
    if any(w in blob for w in ("keyboard", "kbd", "keychron")):
        return "keyboard"
    if any(w in blob for w in ("headset", "headphone", "earbud", "airpod", "buds", "epos", "arctis", "cloud", "audio")):
        return "headset"
    if any(w in blob for w in ("gamepad", "controller", "dualsense", "dualshock", "xbox", "joy-con", "pro controller", "gaming-input", "gaming_input")):
        return "gamepad"
    if any(w in blob for w in ("tablet", "wacom", "pen", "stylus", "touchpad")):
        return "tablet"
    return "device"


def _clean_name(vendor: str, model: str, fallback: str) -> str:
    v = vendor.strip()
    m = model.strip()
    if m and v and not m.lower().startswith(v.lower()):
        return f"{v} {m}"
    return m or v or fallback


# ---------- 1. /sys/class/power_supply (scope=Device) ----------

def read_sysfs_batteries(base: str = POWER_SUPPLY) -> list[PeripheralBattery]:
    """Read peripheral batteries from /sys/class/power_supply (scope=Device)."""
    root = Path(base)
    try:
        entries = sorted(p for p in root.iterdir() if p.is_dir())
    except OSError:
        return []

    found: list[PeripheralBattery] = []
    for entry in entries:
        if _LAPTOP_BAT_RE.match(entry.name):
            continue
        ps_type = (sysfs.read_text(entry / "type") or "").strip()
        scope = (sysfs.read_text(entry / "scope") or "").strip()
        if ps_type != "Battery" or scope != "Device":
            continue

        cap_raw = sysfs.read_text(entry / "capacity")
        percent: int | None = None
        if cap_raw is not None:
            try:
                percent = max(0, min(100, int(float(cap_raw))))
            except ValueError:
                percent = None
        level = (sysfs.read_text(entry / "capacity_level") or "").strip()
        if percent is None and not level:
            continue

        model = sysfs.read_text(entry / "model_name") or ""
        vendor = sysfs.read_text(entry / "manufacturer") or ""
        serial = sysfs.read_text(entry / "serial_number") or ""
        status = _norm_status(sysfs.read_text(entry / "status") or "")
        name = _clean_name(vendor, model, entry.name)
        key = _norm_key(serial) or _norm_key(entry.name)
        found.append(
            PeripheralBattery(
                name=name,
                percent=percent,
                status=status,
                kind=_guess_kind(name, entry.name),
                source="sysfs",
                key=key,
                level=level,
            )
        )
    return found


# ---------- 2. UPower (`upower -d`) ----------

def parse_upower(text: str) -> list[PeripheralBattery]:
    """Parse `upower -d` output and return non-system peripheral batteries."""
    if not text.strip():
        return []

    blocks = re.split(r"(?m)^Device:\s+", text)
    found: list[PeripheralBattery] = []
    for block in blocks[1:]:
        lines = block.splitlines()
        if not lines:
            continue
        dev_path = lines[0].strip()
        dev_base = dev_path.rsplit("/", 1)[-1]
        if dev_base == "DisplayDevice" or dev_base.startswith("line_power_"):
            continue

        fields: dict[str, str] = {}
        section = ""
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if not line.startswith("    ") and ":" not in stripped:
                section = stripped.lower()
                continue
            if ":" in stripped:
                k, v = stripped.split(":", 1)
                fields[k.strip().lower()] = v.strip()

        power_supply = fields.get("power supply", "").lower()
        is_periph_prefix = dev_base.startswith(_UPOWER_PERIPH_PREFIXES)
        # Skip the laptop's own main battery (power supply: yes and battery_BAT*)
        if power_supply == "yes" and not is_periph_prefix:
            continue
        if fields.get("present", "yes").lower() == "no":
            continue

        pct_raw = fields.get("percentage", "")
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", pct_raw)
        percent: int | None = None
        if pct_match:
            percent = max(0, min(100, round(float(pct_match.group(1)))))
        level = fields.get("battery-level", "")
        if level.lower() in ("", "none", "unknown"):
            level = ""
        if percent is None and not level:
            continue

        native = fields.get("native-path", "")
        if _LAPTOP_BAT_RE.match(native) and not is_periph_prefix:
            continue

        vendor = fields.get("vendor", "")
        model = fields.get("model", "")
        serial = fields.get("serial", "")
        icon = fields.get("icon-name", "")
        name = _clean_name(vendor, model, native or dev_base)
        status = _norm_status(fields.get("state", ""))
        kind = _guess_kind(name, f"{dev_base} {section} {icon}")
        key = _norm_key(serial) or _norm_key(native) or _norm_key(dev_base)
        found.append(
            PeripheralBattery(
                name=name,
                percent=percent,
                status=status,
                kind=kind,
                source="upower",
                key=key,
                level=level,
            )
        )
    return found


def read_upower_batteries() -> list[PeripheralBattery]:
    if shutil.which("upower") is None:
        return []
    try:
        proc = subprocess.run(["upower", "-d"], capture_output=True, text=True, timeout=4)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    return parse_upower(proc.stdout)


# ---------- 3. Optional `headsetcontrol` ----------

def parse_headsetcontrol(text: str) -> list[PeripheralBattery]:
    """Parse `headsetcontrol -b -o json` (v3+) or legacy `headsetcontrol -b` output."""
    stripped = text.strip()
    if not stripped:
        return []

    # JSON output (HeadsetControl v3+)
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(stripped)
        except ValueError:
            return []
        devices = data.get("devices", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        found: list[PeripheralBattery] = []
        for dev in devices:
            if not isinstance(dev, dict):
                continue
            bat = dev.get("battery") or {}
            if not isinstance(bat, dict):
                continue
            raw_status = str(bat.get("status", "")).upper()
            if "UNAVAILABLE" in raw_status or "ERROR" in raw_status:
                continue
            lvl = bat.get("level")
            percent = max(0, min(100, int(lvl))) if isinstance(lvl, (int, float)) and lvl >= 0 else None
            if percent is None:
                continue
            status = "charging" if "CHARGING" in raw_status else "discharging"
            name = str(dev.get("device") or dev.get("product") or "USB Headset").strip()
            found.append(
                PeripheralBattery(
                    name=name,
                    percent=percent,
                    status=status,
                    kind="headset",
                    source="headsetcontrol",
                    key=_norm_key(name),
                )
            )
        return found

    # Legacy plain text output: "Found <Name>!\nBattery: 75%" or "Battery: Charging"
    name_match = re.search(r"^Found\s+(.+?)!?\s*$", stripped, re.M)
    bat_match = re.search(r"Battery:\s*(.+)$", stripped, re.M | re.I)
    if not bat_match:
        return []
    val = bat_match.group(1).strip()
    if "unavailable" in val.lower() or "error" in val.lower():
        return []
    pct_m = re.search(r"(\d+)\s*%", val)
    percent = max(0, min(100, int(pct_m.group(1)))) if pct_m else None
    status = "charging" if "charging" in val.lower() else "discharging"
    if percent is None and status != "charging":
        return []
    name = name_match.group(1).strip() if name_match else "USB Headset"
    return [
        PeripheralBattery(
            name=name,
            percent=percent,
            status=status,
            kind="headset",
            source="headsetcontrol",
            key=_norm_key(name),
        )
    ]


def read_headsetcontrol_batteries() -> list[PeripheralBattery]:
    if shutil.which("headsetcontrol") is None:
        return []
    for args in (["headsetcontrol", "-b", "-o", "json"], ["headsetcontrol", "-b"]):
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=4)
        except (OSError, subprocess.TimeoutExpired):
            return []
        if proc.returncode == 0 and proc.stdout.strip():
            parsed = parse_headsetcontrol(proc.stdout)
            if parsed:
                return parsed
    return []


# ---------- merging & deduplication ----------

def merge_batteries(
    *lists: list[PeripheralBattery],
    bluetooth_devices: list[dict] | None = None,
) -> list[dict]:
    """Deduplicate peripheral batteries across sysfs, UPower, headsetcontrol and Bluetooth."""
    items: list[PeripheralBattery] = []
    for lst in lists:
        items.extend(lst)
    for bt in bluetooth_devices or []:
        pct = bt.get("battery")
        if pct is None or (isinstance(pct, int) and pct < 0):
            continue
        name = str(bt.get("name") or "").strip()
        if not name:
            continue
        items.append(
            PeripheralBattery(
                name=name,
                percent=max(0, min(100, int(pct))),
                status="unknown",
                kind=_guess_kind(name, str(bt.get("icon") or "")),
                source="bluetooth",
                key=_norm_key(name),
            )
        )

    merged: list[PeripheralBattery] = []
    for item in items:
        name_key = _norm_key(item.name)
        dup_idx = None
        for idx, existing in enumerate(merged):
            if (item.key and existing.key and item.key == existing.key) or (
                name_key and name_key == _norm_key(existing.name)
            ):
                dup_idx = idx
                break
        if dup_idx is None:
            merged.append(item)
            continue
        old = merged[dup_idx]
        # Prefer the entry with an exact percentage, richer status, or longer human name
        old_score = (old.percent is not None, old.status != "unknown", len(old.name))
        new_score = (item.percent is not None, item.status != "unknown", len(item.name))
        if new_score > old_score:
            merged[dup_idx] = PeripheralBattery(
                name=item.name if len(item.name) >= len(old.name) else old.name,
                percent=item.percent if item.percent is not None else old.percent,
                status=item.status if item.status != "unknown" else old.status,
                kind=item.kind if item.kind != "device" else old.kind,
                source=item.source,
                key=item.key or old.key,
                level=item.level or old.level,
            )
        else:
            # Fill missing status or kind from the second source
            merged[dup_idx] = PeripheralBattery(
                name=old.name,
                percent=old.percent if old.percent is not None else item.percent,
                status=old.status if old.status != "unknown" else item.status,
                kind=old.kind if old.kind != "device" else item.kind,
                source=old.source,
                key=old.key or item.key,
                level=old.level or item.level,
            )

    return [
        {
            "name": b.name,
            "percent": -1 if b.percent is None else b.percent,
            "status": b.status,
            "kind": b.kind,
            "source": b.source,
            "level": b.level,
        }
        for b in merged
    ]


def enrich_bluetooth(bt_devices: list[dict], batteries: list[dict]) -> list[dict]:
    """Fill missing Bluetooth battery percentages using UPower/sysfs readings matched by name."""
    by_name = {_norm_key(b["name"]): b["percent"] for b in batteries if b.get("percent", -1) >= 0}
    out = []
    for d in bt_devices:
        item = dict(d)
        if item.get("battery", -1) < 0:
            found = by_name.get(_norm_key(str(item.get("name") or "")))
            if found is not None:
                item["battery"] = found
        out.append(item)
    return out


def collect(
    bluetooth_devices: list[dict] | None = None,
    power_supply_base: str = POWER_SUPPLY,
) -> list[dict]:
    """Read and merge peripheral batteries from all available sources (read only)."""
    return merge_batteries(
        read_upower_batteries(),
        read_sysfs_batteries(power_supply_base),
        read_headsetcontrol_batteries(),
        bluetooth_devices=bluetooth_devices,
    )
