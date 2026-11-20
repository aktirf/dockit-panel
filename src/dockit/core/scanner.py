"""First-run scan: which features exist on this laptop and in what state.

The scan only READS. It never changes anything on the system.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from typing import Any

from . import i18n, sysfs
from .module import Module
from .status import Status

DMI = "/sys/class/dmi/id"


@dataclass
class ScanItem:
    id: str
    name: str
    source: str
    status: Status
    detail: str
    state: Any = None
    hint: str = ""


@dataclass
class ScanResult:
    system: dict[str, str] = field(default_factory=dict)
    items: list[ScanItem] = field(default_factory=list)
    peripherals: list = field(default_factory=list)  # PeripheralItem objects
    laptop: Any = None                               # DeviceEntry if the laptop is in the database

    def counts(self) -> dict[Status, int]:
        return {s: sum(1 for i in self.items if i.status is s) for s in Status}


def display_name(system: dict[str, str]) -> str:
    """"GIGABYTE GAMING A16 3VH": the vendor is not repeated if the model already starts with it."""
    vendor = system.get("vendor", "")
    model = system.get("model", "")
    if vendor and model.lower().startswith(vendor.lower()):
        return model
    return f"{vendor} {model}".strip()


def system_info() -> dict[str, str]:
    """Model and OS info. No serial numbers, no hostname, no user names."""
    info = {
        "vendor": sysfs.read_text(f"{DMI}/sys_vendor") or "unknown",
        "model": sysfs.read_text(f"{DMI}/product_name") or "unknown",
        "bios": sysfs.read_text(f"{DMI}/bios_version") or "unknown",
        "kernel": platform.release(),
        "distro": _distro(),
    }
    return info


def _distro() -> str:
    text = sysfs.read_text("/etc/os-release") or ""
    for line in text.splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip('"')
    return "unknown"


def scan(
    modules: list[type[Module]] | None = None,
    peripherals: bool = True,
) -> ScanResult:
    if modules is None:
        from ..modules import ALL_MODULES

        modules = ALL_MODULES

    result = ScanResult(system=system_info())
    if peripherals:
        _scan_devices(result)
    for cls in modules:
        mod = cls()
        try:
            det = mod.detect()
            state = mod.get_state() if det.status is not Status.UNAVAILABLE else None
            hint = mod.fix_hint() if det.status is not Status.OK else ""
            item = ScanItem(mod.id, mod.name, mod.source, det.status, det.detail, state, hint)
        except Exception as exc:  # a broken module must never break the whole scan
            item = ScanItem(
                mod.id, mod.name, mod.source, Status.UNAVAILABLE,
                f"Ошибка проверки: {type(exc).__name__}",
            )
        result.items.append(item)
    return result


def _scan_devices(result: ScanResult) -> None:
    """Match the laptop and connected USB devices against the device database."""
    try:
        from ..peripherals.database import find_laptop, load_database
        from ..peripherals.scan import scan_peripherals

        entries = load_database()
        result.laptop = find_laptop(entries, result.system.get("model", ""))
        result.peripherals = scan_peripherals(entries=entries)
    except Exception:  # devices are optional, they must never break the scan
        pass


_STATUS_KEYS = {
    Status.OK: "status_ok",
    Status.NEEDS_SETUP: "status_setup",
    Status.NEEDS_ROOT: "status_root",
    Status.UNAVAILABLE: "status_no",
}

_BAT_STATE_KEYS = {
    "Charging": "bat_charging",
    "Discharging": "bat_discharging",
    "Full": "bat_full",
    "Not charging": "bat_not_charging",
}


def localize_item(item: ScanItem, lang: str = "ru") -> tuple[str, str, str]:
    """Return localized (name, detail, hint) for a ScanItem in lang ('ru'/'en'/'uk').

    When lang is 'ru', modules already produce Russian strings, so custom/test
    ScanItems keep their exact text unchanged.
    """
    lang = i18n.resolve_lang(lang)
    if lang == "ru":
        return item.name, item.detail, item.hint

    mid = item.id
    st = item.status
    state = item.state
    name_key = f"mod_{mid}_name"
    name = i18n.tr(name_key, lang)
    if name == name_key:
        return item.name, item.detail, item.hint

    detail = item.detail
    hint = item.hint

    if mid == "service":
        detail = i18n.tr("mod_service_ok" if st is Status.OK else "mod_service_setup", lang)
        if hint:
            hint = i18n.tr("mod_service_hint", lang)
    elif mid == "power_profile":
        detail = i18n.tr(
            "mod_power_profile_ok" if st is Status.OK else (
                "mod_power_profile_setup" if st is Status.NEEDS_SETUP else "mod_power_profile_no"
            ),
            lang,
        )
        if hint:
            hint = i18n.tr("mod_power_profile_hint_no" if st is Status.UNAVAILABLE else "mod_power_profile_hint_setup", lang)
    elif mid == "sensors":
        if st is Status.OK:
            has_fans = bool(isinstance(state, dict) and state.get("fans_rpm"))
            detail = i18n.tr("mod_sensors_ok_fans" if has_fans else "mod_sensors_ok_nofans", lang)
        else:
            detail = i18n.tr("mod_sensors_no", lang)
        if hint:
            hint = i18n.tr("mod_sensors_hint", lang)
    elif mid == "gpu_nvidia":
        if st is Status.OK:
            if isinstance(state, dict) and state.get("asleep"):
                detail = i18n.tr("mod_gpu_nvidia_ok_asleep", lang)
            elif isinstance(state, dict) and state.get("name"):
                detail = i18n.tr("mod_gpu_nvidia_ok_name", lang, name=state["name"])
        elif st is Status.NEEDS_SETUP:
            detail = i18n.tr("mod_gpu_nvidia_setup", lang)
        else:
            detail = i18n.tr("mod_gpu_nvidia_no", lang)
        if hint:
            hint = i18n.tr("mod_gpu_nvidia_hint", lang)
    elif mid == "battery":
        bats = state.get("batteries", []) if isinstance(state, dict) else []
        if st is Status.OK and bats and bats[0].get("percent") is not None:
            b = bats[0]
            bkey = _BAT_STATE_KEYS.get(b.get("status") or "")
            bstatus = i18n.tr(bkey, lang).lower() if bkey else i18n.tr("no_data_lower", lang)
            detail = i18n.tr("mod_battery_ok", lang, pct=b["percent"], status=bstatus)
        elif st is not Status.OK:
            detail = i18n.tr("mod_battery_no", lang)
    elif mid == "battery_limit":
        detail = i18n.tr(
            "mod_battery_limit_ok" if st is Status.OK else (
                "mod_battery_limit_setup" if st is Status.NEEDS_SETUP else "mod_battery_limit_no"
            ),
            lang,
        )
        if hint:
            hint = i18n.tr("mod_battery_limit_hint_no" if st is Status.UNAVAILABLE else "mod_battery_limit_hint_setup", lang)
    elif mid == "camera":
        detail = i18n.tr(
            "mod_camera_ok" if st is Status.OK else (
                "mod_camera_setup" if st is Status.NEEDS_SETUP else "mod_camera_no"
            ),
            lang,
        )
        if hint:
            hint = i18n.tr("mod_camera_hint", lang)
    elif mid == "wireless":
        if st is Status.OK and isinstance(state, dict) and state:
            detail = i18n.tr("mod_wireless_ok", lang, mods=", ".join(state))
        elif st is not Status.OK:
            detail = i18n.tr("mod_wireless_no", lang)
        if hint:
            hint = i18n.tr("mod_wireless_hint", lang)
    elif mid == "audio":
        if st is Status.OK and isinstance(state, list):
            outs = [d for d in state if d.get("kind") == "output"]
            ins = [d for d in state if d.get("kind") == "input"]
            cur = next((d.get("description", "") for d in outs if d.get("default")), outs[0].get("description", "") if outs else "")
            detail = i18n.tr("mod_audio_ok", lang, outs=len(outs), ins=len(ins), cur=cur)
        elif st is not Status.OK:
            detail = i18n.tr("mod_audio_no", lang)
        if hint:
            hint = i18n.tr("mod_audio_hint", lang)
    elif mid == "kbd_backlight":
        devs = state.get("devices", []) if isinstance(state, dict) else []
        if devs:
            names = ", ".join(str(d.get("name", "")) for d in devs)
            mode = "HID LampArray RGB" if any(d.get("rgb") for d in devs) else "LED"
            key = "mod_kbd_backlight_ok" if st is Status.OK else "mod_kbd_backlight_setup"
            detail = i18n.tr(key, lang, names=names, mode=mode)
        else:
            detail = i18n.tr("mod_kbd_backlight_no", lang)
        if hint:
            hint = i18n.tr("mod_kbd_backlight_hint_setup" if devs else "mod_kbd_backlight_hint_no", lang)

    return name, detail, hint


def format_report(result: ScanResult, lang: str | None = None) -> str:
    """Plain text report the user can paste into a GitHub issue, localized to lang."""
    resolved = i18n.resolve_lang(lang)
    lines = ["DOCKIT report", ""]
    for key, value in result.system.items():
        lines.append(f"{key}: {value}")
    db_lbl = i18n.tr("report_laptop_db", resolved)
    if result.laptop:
        lines.append(f"{db_lbl}: {i18n.tr('report_yes', resolved)} ({result.laptop.status})")
    else:
        lines.append(f"{db_lbl}: {i18n.tr('report_no', resolved)}")
    lines.append("")
    fix_lbl = i18n.tr("report_fix", resolved)
    for item in result.items:
        name, detail, hint = localize_item(item, resolved)
        status_text = i18n.tr(_STATUS_KEYS[item.status], resolved)
        lines.append(f"[{status_text}] {name} ({item.source})")
        lines.append(f"    {detail}")
        if hint:
            lines.append(f"    {fix_lbl}: {hint}")
    if result.peripherals:
        lines.append("")
        lines.append(i18n.tr("report_usb", resolved) + ":")
        not_in_db = i18n.tr("report_not_in_db", resolved)
        for p in result.peripherals:
            tag = p.status if p.known else not_in_db
            lines.append(f"    {p.usb_id}  {p.name}  [{tag}]")
    counts = result.counts()
    lines.append("")
    lines.append(
        i18n.tr("report_total", resolved)
        + ": "
        + ", ".join(f"{i18n.tr(_STATUS_KEYS[s], resolved)}: {counts[s]}" for s in Status)
    )
    return "\n".join(lines)
