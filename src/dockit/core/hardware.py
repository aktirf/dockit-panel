"""First-run hardware inspection & compatibility summary (laptop/desktop, AMD/Intel).

Pure logic with no Qt imports so Intel laptops, AMD laptops, and desktop PCs can all
be unit-tested cleanly with synthetic sysfs fixtures.
"""

from __future__ import annotations

import os

from . import i18n, sysfs
from .scanner import ScanResult, display_name, localize_item
from .status import Status

DMI = "/sys/class/dmi/id"

# Standard SMBIOS chassis type codes
_LAPTOP_CHASSIS = {8, 9, 10, 11, 14, 30, 31, 32}
_DESKTOP_CHASSIS = {3, 4, 5, 6, 7, 13, 15, 16, 24, 35, 36}

_MODULE_ICONS = {
    "service": "zap",
    "power_profile": "gauge",
    "sensors": "flame",
    "gpu_nvidia": "monitor",
    "battery": "battery",
    "battery_limit": "battery",
    "camera": "camera",
    "wireless": "wifi",
    "audio": "speaker",
    "kbd_backlight": "keyboard",
}


def detect_form_factor(dmi_dir: str = DMI, has_battery: bool | None = None) -> str:
    """Return 'laptop' or 'desktop' from SMBIOS chassis_type with battery fallback."""
    raw = sysfs.read_text(f"{dmi_dir}/chassis_type")
    if raw and raw.isdigit():
        code = int(raw)
        if code in _LAPTOP_CHASSIS:
            return "laptop"
        if code in _DESKTOP_CHASSIS:
            return "desktop"
    if has_battery is True:
        return "laptop"
    if has_battery is False:
        return "desktop"
    return "laptop"


def detect_cpu_vendor(cpu_name: str, cpu_driver: str = "") -> str:
    low = (cpu_name or "").lower()
    drv = (cpu_driver or "").lower()
    if "amd" in low or "ryzen" in low or "epyc" in low or "amd" in drv:
        return "amd"
    if "intel" in low or "core(" in low or "xeon" in low or "intel" in drv:
        return "intel"
    return "other"


def detect_desktop(env: dict[str, str] | None = None) -> str:
    src = os.environ if env is None else env
    if src.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "Hyprland"
    if src.get("NIRI_SOCKET"):
        return "niri"
    if src.get("SWAYSOCK"):
        return "Sway"
    cur = (src.get("XDG_CURRENT_DESKTOP") or src.get("DESKTOP_SESSION") or "").strip()
    low = cur.lower()
    if "hyprland" in low:
        return "Hyprland"
    if "niri" in low:
        return "niri"
    if "sway" in low:
        return "Sway"
    if "kde" in low or "plasma" in low:
        return "KDE Plasma"
    if "gnome" in low:
        return "GNOME"
    if cur:
        return cur
    if src.get("WAYLAND_DISPLAY"):
        return "Wayland"
    if src.get("DISPLAY"):
        return "X11"
    return "Linux"


def build_welcome(
    result: ScanResult,
    cpu_name: str,
    tuning_info: dict | None,
    display_info: dict | None,
    idle_available: bool = False,
    lang: str = "ru",
    *,
    amd_gpu: dict | None = None,
    dmi_dir: str = DMI,
    env: dict[str, str] | None = None,
) -> dict:
    """Build the first-run hardware report shown in WelcomePage."""
    tuning = tuning_info or {}
    disp = display_info or {}

    by_id = {item.id: item for item in result.items}
    bat_item = by_id.get("battery")
    has_battery = bool(bat_item and bat_item.status is Status.OK)
    form_factor = detect_form_factor(dmi_dir=dmi_dir, has_battery=has_battery)
    cpu_driver = str(tuning.get("driver") or "")
    cpu_vendor = detect_cpu_vendor(cpu_name, cpu_driver)
    desktop = detect_desktop(env)

    gpu_item = by_id.get("gpu_nvidia")
    gpu_name = ""
    if gpu_item and isinstance(gpu_item.state, dict) and gpu_item.state.get("name"):
        gpu_name = str(gpu_item.state["name"])
    elif isinstance(amd_gpu, dict) and amd_gpu.get("name"):
        gpu_name = str(amd_gpu["name"])

    working: list[dict] = []
    needs_setup: list[dict] = []
    unavailable: list[dict] = []

    for item in result.items:
        title, detail, hint = localize_item(item, lang)
        icon = _MODULE_ICONS.get(item.id, "pulse")
        if item.status is Status.OK:
            working.append({"id": item.id, "icon": icon, "title": title, "detail": detail})
        elif item.status in (Status.NEEDS_SETUP, Status.NEEDS_ROOT):
            needs_setup.append({
                "id": item.id,
                "icon": icon,
                "title": title,
                "detail": detail,
                "hint": hint,
            })
        else:
            if item.id == "gpu_nvidia" and isinstance(amd_gpu, dict) and amd_gpu.get("name"):
                working.append({
                    "id": "gpu_amd",
                    "icon": "monitor",
                    "title": i18n.tr("welcome_gpu_amd_title", lang),
                    "detail": i18n.tr("welcome_gpu_amd_ok", lang, name=amd_gpu["name"]),
                })
                continue
            reason = detail
            if item.id == "battery" and form_factor == "desktop":
                reason = i18n.tr("welcome_desktop_no_battery", lang)
            elif item.id == "battery_limit" and form_factor == "desktop":
                continue  # desktop PC has no battery at all, no need to repeat
            unavailable.append({"id": item.id, "icon": icon, "title": title, "detail": reason})

    # CPU fine tuning & Dynamic CPU mode (works on both AMD and Intel; dynamic is AMD 7.x+)
    epp_choices = list(tuning.get("eppChoices") or [])
    has_dynamic = bool(tuning.get("hasDynamic"))
    has_boost = tuning.get("boost") is not None

    if has_dynamic:
        working.append({
            "id": "dynamic_cpu",
            "icon": "zap",
            "title": i18n.tr("mode_dynamic", lang),
            "detail": i18n.tr("welcome_dynamic_ok", lang),
        })
    else:
        unavailable.append({
            "id": "dynamic_cpu",
            "icon": "zap",
            "title": i18n.tr("mode_dynamic", lang),
            "detail": i18n.tr(
                "welcome_dynamic_intel" if cpu_vendor == "intel" else "welcome_dynamic_no",
                lang,
            ),
        })

    manual_epp = [c for c in epp_choices if c not in ("custom", "dynamic")]
    if manual_epp or has_boost:
        parts = []
        if has_boost:
            parts.append("Turbo Boost")
        if manual_epp:
            parts.append(f"EPP ({cpu_driver or cpu_vendor.upper()})")
        working.append({
            "id": "cpu_tuning",
            "icon": "cpu",
            "title": i18n.tr("welcome_cpu_tuning", lang),
            "detail": ", ".join(parts),
        })
    else:
        unavailable.append({
            "id": "cpu_tuning",
            "icon": "cpu",
            "title": i18n.tr("welcome_cpu_tuning", lang),
            "detail": i18n.tr("epp_unavailable", lang),
        })

    # Display refresh rate & brightness
    rates = list(disp.get("rates") or [])
    if rates:
        working.append({
            "id": "display_refresh",
            "icon": "monitor",
            "title": i18n.tr("screen_refresh", lang),
            "detail": i18n.tr(
                "welcome_refresh_ok",
                lang,
                rates=", ".join(str(r) for r in rates),
                desktop=desktop,
            ),
        })
    else:
        unavailable.append({
            "id": "display_refresh",
            "icon": "monitor",
            "title": i18n.tr("screen_refresh", lang),
            "detail": i18n.tr("refresh_missing", lang),
        })

    # Fan speed visibility note (sensors module is OK for temps even when fans are hidden)
    sensors_item = by_id.get("sensors")
    if sensors_item and sensors_item.status is Status.OK:
        fans = (sensors_item.state or {}).get("fans_rpm") if isinstance(sensors_item.state, dict) else {}
        if not fans:
            unavailable.append({
                "id": "fans",
                "icon": "fan",
                "title": i18n.tr("fans", lang),
                "detail": i18n.tr("fans_missing", lang),
            })

    # AFK auto-rules helper
    if not idle_available:
        needs_setup.append({
            "id": "swayidle",
            "icon": "clock",
            "title": i18n.tr("rule_idle_title", lang),
            "detail": i18n.tr("swayidle_missing", lang),
            "hint": "",
        })

    cpu_vendor_label = {"amd": "AMD", "intel": "Intel"}.get(cpu_vendor, "CPU")
    return {
        "formFactor": form_factor,
        "formLabel": i18n.tr("welcome_laptop" if form_factor == "laptop" else "welcome_desktop", lang),
        "model": display_name(result.system) or i18n.tr("app_laptop", lang),
        "cpu": cpu_name or cpu_vendor_label,
        "cpuVendor": cpu_vendor,
        "cpuVendorLabel": cpu_vendor_label,
        "cpuDriver": cpu_driver,
        "gpu": gpu_name or i18n.tr("welcome_gpu_integrated", lang),
        "desktop": desktop,
        "kernel": str(result.system.get("kernel") or ""),
        "working": working,
        "needsSetup": needs_setup,
        "unavailable": unavailable,
    }
