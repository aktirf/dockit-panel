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
        if st is Status.OK and isinstance(state, dict):
            if state.get("kind") == "conservation":
                detail = i18n.tr(
                    "mod_battery_limit_cons_on" if state.get("conservation") else "mod_battery_limit_cons_off",
                    lang,
                )
            elif state.get("value") is not None:
                detail = i18n.tr("mod_battery_limit_ok_pct", lang, pct=state["value"])
            else:
                detail = i18n.tr("mod_battery_limit_ok", lang)
        else:
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


def collect_environment_details(result: ScanResult | None = None) -> dict[str, str]:
    """Read-only snapshot of CPU, GPU, display, and laptop driver details for bug/device reports.

    Never reads serial numbers, hostnames, or usernames, and never wakes a sleeping NVIDIA GPU.
    """
    import glob
    import shutil
    from . import battery_limit, cpu, display, gpu_amd, hardware, idle, tuning

    details: dict[str, str] = {}
    cpu_name = cpu.CpuMonitor().name()
    if cpu_name:
        details["cpu"] = cpu_name
    drv = tuning.cpu_driver()
    if drv:
        details["cpu_driver"] = drv
    epp = tuning.epp_choices()
    if epp:
        details["epp_choices"] = " ".join(epp)
    boost = tuning.read_boost()
    if boost is not None:
        details["turbo_boost"] = "on" if boost else "off"
    acpi_choices = sysfs.read_text("/sys/firmware/acpi/platform_profile_choices")
    if acpi_choices:
        details["acpi_profiles"] = acpi_choices
    details["desktop"] = hardware.detect_desktop()
    has_bat = None
    if result is not None:
        bat = next((i for i in result.items if i.id == "battery"), None)
        if bat is not None:
            has_bat = bat.status is Status.OK
    details["form_factor"] = hardware.detect_form_factor(has_battery=has_bat)

    try:
        disp = display.refresh_info()
        if disp.get("output"):
            rates = ", ".join(f"{r}Hz" for r in (disp.get("rates") or []))
            details["display"] = f"{disp['output']} ({disp.get('current')}Hz; rates: {rates or 'none'})"
    except Exception:
        pass

    lim = battery_limit.discover()
    if lim is not None:
        details["battery_limit"] = f"{lim['kind']}={lim.get('value')}%"

    amd = gpu_amd.summary()
    if amd is not None:
        details["amd_gpu"] = f"{amd['name']} (asleep={amd['asleep']})"

    hwmons = []
    for hm in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        name = sysfs.read_text(f"{hm}/name")
        if name:
            fans = len(glob.glob(f"{hm}/fan*_input"))
            hwmons.append(f"{name}({fans}f)" if fans else name)
    if hwmons:
        details["hwmon"] = ", ".join(hwmons[:12])

    helpers = []
    if shutil.which("powerprofilesctl"):
        helpers.append("power-profiles-daemon")
    if idle.available():
        helpers.append("swayidle")
    if shutil.which("notify-send"):
        helpers.append("libnotify")
    if helpers:
        details["helpers"] = ", ".join(helpers)
    return details


def format_report(
    result: ScanResult,
    lang: str | None = None,
    *,
    markdown: bool = False,
    env_details: dict[str, str] | None = None,
) -> str:
    """Plain text or GitHub Markdown report the user can paste into a GitHub issue."""
    from .. import __version__

    resolved = i18n.resolve_lang(lang)
    details = collect_environment_details(result) if env_details is None else env_details
    counts = result.counts()
    db_lbl = i18n.tr("report_laptop_db", resolved)
    db_val = (
        f"{i18n.tr('report_yes', resolved)} ({result.laptop.status})"
        if result.laptop else i18n.tr("report_no", resolved)
    )
    fix_lbl = i18n.tr("report_fix", resolved)

    if markdown:
        lines = [
            f"### DOCKIT report (`v{__version__}`)",
            "",
            "| Field | Value |",
            "| --- | --- |",
        ]
        for key, value in result.system.items():
            lines.append(f"| `{key}` | {value} |")
        lines.append(f"| `{db_lbl}` | {db_val} |")
        for key, value in details.items():
            lines.append(f"| `{key}` | {value} |")
        lines.append("")
        lines.append(
            "**" + i18n.tr("report_total", resolved) + ":** "
            + ", ".join(f"{i18n.tr(_STATUS_KEYS[s], resolved)}: {counts[s]}" for s in Status)
        )
        lines.append("")
        lines.append("<details>")
        lines.append(f"<summary>{i18n.tr('report_features_summary', resolved)}</summary>")
        lines.append("")
        lines.append("```text")
        for item in result.items:
            name, detail, hint = localize_item(item, resolved)
            status_text = i18n.tr(_STATUS_KEYS[item.status], resolved)
            lines.append(f"[{status_text}] {name} ({item.source})")
            lines.append(f"    {detail}")
            if hint:
                lines.append(f"    {fix_lbl}: {hint}")
        lines.append("```")
        lines.append("</details>")
        if result.peripherals:
            not_in_db = i18n.tr("report_not_in_db", resolved)
            lines.append("")
            lines.append("<details>")
            lines.append(f"<summary>{i18n.tr('report_usb', resolved)} ({len(result.peripherals)})</summary>")
            lines.append("")
            lines.append("```text")
            for p in result.peripherals:
                tag = p.status if p.known else not_in_db
                lines.append(f"{p.usb_id}  {p.name}  [{tag}]")
            lines.append("```")
            lines.append("</details>")
        return "\n".join(lines)

    lines = [f"DOCKIT report (v{__version__})", ""]
    for key, value in result.system.items():
        lines.append(f"{key}: {value}")
    for key, value in details.items():
        lines.append(f"{key}: {value}")
    lines.append(f"{db_lbl}: {db_val}")
    lines.append("")
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
    lines.append("")
    lines.append(
        i18n.tr("report_total", resolved)
        + ": "
        + ", ".join(f"{i18n.tr(_STATUS_KEYS[s], resolved)}: {counts[s]}" for s in Status)
    )
    return "\n".join(lines)
