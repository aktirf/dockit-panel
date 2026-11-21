"""Turns scan results into plain data for the window.

No Qt here, so it can be tested without a screen. Everything returned is
simple dicts, lists, strings, numbers and booleans.
"""

from __future__ import annotations

import shutil

from ..core import i18n
from ..core.profiles import DEFAULT_PROFILES
from ..modules.battery import minutes_left
from ..core.scanner import ScanResult, display_name, localize_item
from ..core.status import LABELS_RU, Status
from ..peripherals.scan import KIND_RU

MODES = [
    {"id": "low-power", "name": "Тишина", "hint": "Тихо и экономно"},
    {"id": "balanced", "name": "Баланс", "hint": "Мощность и шум в равновесии"},
    {"id": "performance", "name": "Производительность", "hint": "Максимум мощности"},
]

STATUS_KEY = {
    Status.OK: "ok",
    Status.NEEDS_SETUP: "setup",
    Status.NEEDS_ROOT: "root",
    Status.UNAVAILABLE: "no",
}

BATTERY_TEXT = {
    "Full": "Полностью заряжена",
    "Charging": "Заряжается",
    "Discharging": "Разряжается",
    "Not charging": "Не заряжается",
}

_BAT_KEYS = {
    "Full": "bat_full",
    "Charging": "bat_charging",
    "Discharging": "bat_discharging",
    "Not charging": "bat_not_charging",
}

_CHIP_KEYS = {
    "k10temp": "chip_cpu", "zenpower": "chip_cpu", "coretemp": "chip_cpu",
    "nvme": "chip_nvme", "amdgpu": "chip_igpu", "nouveau": "chip_gpu",
    "nvidia": "chip_gpu", "acpitz": "chip_mb", "BAT0": "chip_bat", "BAT1": "chip_bat",
    "spd5118": "chip_ram", "iwlwifi_1": "chip_wifi", "mt7921_phy0": "chip_wifi", "r8169_0_300:00": "chip_eth",
}


def status_label(status: Status, lang: str = "ru") -> str:
    return i18n.tr(f"status_{STATUS_KEY[status]}", lang)


def modes_for_lang(lang: str = "ru", has_dynamic: bool = False) -> list[dict]:
    items = [
        {"id": "low-power", "name": i18n.tr("mode_low_power", lang), "hint": i18n.tr("mode_low_power_hint", lang)},
        {"id": "balanced", "name": i18n.tr("mode_balanced", lang), "hint": i18n.tr("mode_balanced_hint", lang)},
    ]
    if has_dynamic:
        items.append({"id": "dynamic", "name": i18n.tr("mode_dynamic", lang), "hint": i18n.tr("mode_dynamic_hint", lang)})
    items.append({"id": "performance", "name": i18n.tr("mode_performance", lang), "hint": i18n.tr("mode_performance_hint", lang)})
    return items


def num(value: float | int | None, digits: int = 0) -> str:
    """Number with a decimal comma, "—" if there is no value."""
    if value is None:
        return "—"
    text = f"{value:.{digits}f}"
    return text.replace(".", ",")


def short_model(system: dict[str, str]) -> str:
    name = display_name(system)
    vendor = system.get("vendor", "")
    if vendor and name.lower().startswith(vendor.lower()):
        name = name[len(vendor):].strip()
    return name or "Ноутбук"


def cpu_temperature(sensors_state: dict | None) -> float | None:
    if not sensors_state:
        return None
    best = None
    for key, value in sensors_state.get("temps_c", {}).items():
        chip = key.split("/", 1)[0]
        if chip in ("k10temp", "zenpower", "coretemp") and (best is None or value > best):
            best = value
    return best


CHIP_RU = {
    "k10temp": "Процессор", "zenpower": "Процессор", "coretemp": "Процессор",
    "nvme": "SSD (NVMe)", "amdgpu": "Встроенная графика", "nouveau": "Видеокарта",
    "nvidia": "Видеокарта", "acpitz": "Материнская плата", "BAT0": "Батарея", "BAT1": "Батарея",
    "spd5118": "Память", "iwlwifi_1": "Wi-Fi", "mt7921_phy0": "Wi-Fi", "r8169_0_300:00": "Сетевая карта",
}


def _left_text(b: dict, lang: str = "ru") -> str:
    minutes = minutes_left(b)
    if minutes is None:
        return ""
    h, m = divmod(minutes, 60)
    uh, um = i18n.tr("unit_h", lang), i18n.tr("unit_min", lang)
    text = (f"{h} {uh} " if h else "") + f"{m} {um}"
    key = "bat_left_empty" if b.get("status") == "Discharging" else "bat_left_full"
    return i18n.tr(key, lang, t=text)


# packages DOCKIT may offer to install for a feature (nothing else is ever installed)
FIX_PACKAGES = {
    "sensors": ["lm_sensors"],
    "audio": ["libpulse", "pipewire-pulse"],
    "wireless": ["networkmanager", "bluez-utils"],
    "gpu_nvidia": ["nvidia-open", "nvidia-utils"],
}


def chip_temps(sensors_state: dict | None, lang: str = "ru") -> dict[str, float]:
    """The hottest reading of every chip, by a plain localized name."""
    best: dict[str, float] = {}
    for key, value in ((sensors_state or {}).get("temps_c") or {}).items():
        chip = key.split("/", 1)[0]
        name = i18n.tr(_CHIP_KEYS[chip], lang) if chip in _CHIP_KEYS else CHIP_RU.get(chip, chip)
        best[name] = max(best.get(name, value), value)
    return best


def temperatures(sensors_state: dict | None, lang: str = "ru") -> list[dict]:
    return [{"name": n, "value": f"{v:.0f}", "hot": v >= 85}
            for n, v in sorted(chip_temps(sensors_state, lang).items())]


def _keyboard_leds() -> list[str]:
    import glob
    return [p.rsplit("/", 1)[-1] for p in glob.glob("/sys/class/leds/*kbd*")]


def _item(result: ScanResult, item_id: str):
    return next((i for i in result.items if i.id == item_id), None)


GPU_SLEEP_EMPTY = {"asleep": False, "sleepText": "—", "holders": [], "sleepTip": ""}
KBD_BACKLIGHT_EMPTY = {
    "available": False,
    "can": False,
    "rgb": False,
    "backend": "",
    "deviceName": "",
    "devices": [],
    "on": True,
    "brightness": 100,
    "color": "#5AB0FF",
    "autonomous": False,
}


def kbd_backlight_view(kbd_state: dict | None, service_ok: bool, saved: dict | None = None) -> dict:
    """View dict for the keyboard / LampArray backlight card."""
    devices = list((kbd_state or {}).get("devices") or [])
    if not devices:
        return dict(KBD_BACKLIGHT_EMPTY)
    pref = saved or {}
    first = devices[0]
    rgb = any(bool(d.get("rgb")) for d in devices)
    backend = str(first.get("backend") or "")
    live_brightness = first.get("brightness")
    if not rgb and live_brightness is not None:
        brightness = max(0, min(100, int(live_brightness)))
        on = brightness > 0
        autonomous = False
    else:
        brightness = max(0, min(100, int(pref.get("brightness", 100))))
        on = bool(pref.get("on", True))
        autonomous = bool(pref.get("autonomous", False))
    color = str(pref.get("color") or "#5AB0FF")
    return {
        "available": True,
        "can": bool(service_ok),
        "rgb": rgb,
        "backend": backend,
        "deviceName": ", ".join(str(d.get("name") or "") for d in devices if d.get("name")),
        "devices": devices,
        "on": on,
        "brightness": brightness,
        "color": color,
        "autonomous": autonomous,
    }


_PERIPH_BAT_STATUS = {
    "charging": "periph_bat_charging",
    "full": "periph_bat_full",
    "discharging": "periph_bat_discharging",
}

_PERIPH_BAT_SOURCE = {
    "upower": "UPower",
    "sysfs": "HID / sysfs",
    "headsetcontrol": "HeadsetControl",
    "bluetooth": "Bluetooth",
}


def periph_batteries_view(items: list[dict] | None, lang: str = "ru") -> list[dict]:
    """Localized list of wireless peripheral batteries for PeripheralsPage."""
    out: list[dict] = []
    for item in items or []:
        pct = item.get("percent")
        pct_int = -1 if pct is None else int(pct)
        st = str(item.get("status") or "unknown")
        st_key = _PERIPH_BAT_STATUS.get(st, "")
        status_text = i18n.tr(st_key, lang) if st_key else ""
        src = str(item.get("source") or "")
        out.append({
            "name": str(item.get("name") or ""),
            "percent": pct_int,
            "charging": st == "charging",
            "statusText": status_text,
            "kind": str(item.get("kind") or "device"),
            "source": _PERIPH_BAT_SOURCE.get(src, src),
            "level": str(item.get("level") or ""),
        })
    return out


def gpu_sleep_view(gpu_state: dict | None, lang: str = "ru") -> dict:
    """Is the NVIDIA card asleep and who keeps it awake, as localized text for the window."""
    g = gpu_state or {}
    s = g.get("sleep") or {}
    if not s:
        return {**GPU_SLEEP_EMPTY, "holders": []}
    holders: list[str] = []
    for u in s.get("users") or []:
        if u.get("card") and u.get("name") not in holders:
            holders.append(str(u.get("name")))
    holders = holders[:5]
    if s.get("asleep"):
        text, tip = i18n.tr("gpu_sleep_asleep", lang), i18n.tr("gpu_sleep_asleep_tip", lang)
    elif s.get("control") == "on":
        text, tip = i18n.tr("gpu_sleep_never", lang), i18n.tr("gpu_sleep_never_tip", lang)
    elif holders:
        text = i18n.tr("gpu_sleep_active", lang)
        tip = i18n.tr("gpu_sleep_held_tip", lang, holders=", ".join(holders))
    else:
        text = i18n.tr("gpu_sleep_active", lang) if s.get("runtime") == "active" else "—"
        tip = i18n.tr("gpu_sleep_free_tip", lang)
    return {"asleep": bool(s.get("asleep")), "sleepText": text, "holders": holders, "sleepTip": tip}


def empty() -> dict:
    return {"ready": False, "model": "", "service": False, "okCount": 0, "total": 0,
            "modes": MODES, "currentMode": "", "scenarios": [], "scenario": "",
            "cpu": {"name": "", "freq": "—", "load": None, "temp": "—", "fan": "нет данных", "fanUnit": ""},
            "gpu": {"name": "", "clock": "—", "util": None, "temp": "—", "memUsed": "—", "memTotal": "—",
                    "memPct": 0, "power": "—", "status": "no", "statusText": "", **GPU_SLEEP_EMPTY},
            "battery": {"percent": None, "text": "—", "source": "", "health": "—", "cycles": None,
                        "power": "—", "left": "", "status": "no", "statusText": ""},
            "limit": {"status": "no", "statusText": ""}, "toggles": [], "temps": [], "fans": [],
            "peripherals": [], "periphBatteries": [], "backlight": [], "kbdBacklight": dict(KBD_BACKLIGHT_EMPTY), "system": {},
            "features": [], "counts": [], "cooling": {}, "journal": [], "display": {}, "tuning": {}, "top": [], "bluetooth": [], "batteryHistory": [], "settings": {}, "cpuHistory": [], "gpuHistory": [], "profiles": [],
            "audio": {"outputs": [], "inputs": []}, "apps": [], "idleAvailable": False,
            "fallback": "", "welcome": {}}


def build(result: ScanResult, current_mode: str | None, cpu: dict, cpu_name: str,
          cpu_history: list, gpu_history: list, mic_muted: bool | None,
          scenarios: list[dict], scenario: str, lang: str = "ru",
          kbd_saved: dict | None = None, has_dynamic: bool = False) -> dict:
    service = _item(result, "service")
    sensors = _item(result, "sensors")
    gpu_item = _item(result, "gpu_nvidia")
    bat_item = _item(result, "battery")
    limit_item = _item(result, "battery_limit")
    cam_item = _item(result, "camera")
    wifi_item = _item(result, "wireless")
    kbd_item = _item(result, "kbd_backlight")

    temp = cpu_temperature(sensors.state if sensors else None)
    fans = (sensors.state or {}).get("fans_rpm", {}) if sensors else {}
    fan = max(fans.values()) if fans else None

    g = (gpu_item.state if gpu_item else None) or {}
    gpu = {
        "name": g.get("name", ""),
        "clock": num(g.get("clock_mhz")),
        "util": g.get("util_pct"),
        "temp": num(g.get("temp_c")),
        "memUsed": num(g["mem_used_mb"] / 1024, 1) if g.get("mem_used_mb") is not None else "—",
        "memTotal": num(g["mem_total_mb"] / 1024, 1) if g.get("mem_total_mb") is not None else "—",
        "memPct": round(100 * g["mem_used_mb"] / g["mem_total_mb"]) if g.get("mem_used_mb") is not None and g.get("mem_total_mb") else 0,
        "power": num(g.get("power_w"), 0),
        "status": STATUS_KEY[gpu_item.status] if gpu_item else "no",
        "statusText": status_label(gpu_item.status, lang) if gpu_item else "",
    }
    gpu.update(gpu_sleep_view(g, lang))

    bats = ((bat_item.state if bat_item else None) or {}).get("batteries", [])
    ac = ((bat_item.state if bat_item else None) or {}).get("ac_online")
    b = bats[0] if bats else {}
    bat_status = b.get("status") or ""
    bat_text = i18n.tr(_BAT_KEYS[bat_status], lang) if bat_status in _BAT_KEYS else (bat_status or i18n.tr("no_data", lang))
    battery = {
        "percent": b.get("percent"),
        "text": bat_text,
        "source": i18n.tr("bat_ac", lang) if ac else (i18n.tr("bat_on_battery", lang) if ac is False else ""),
        "health": num(b.get("health_pct"), 0) if b.get("health_pct") is not None else "—",
        "cycles": b.get("cycles"),
        "power": num(b.get("power_w"), 1) if b.get("power_w") else "—",
        "left": _left_text(b, lang),
        "status": STATUS_KEY[bat_item.status] if bat_item else "no",
        "statusText": status_label(bat_item.status, lang) if bat_item else "",
    }
    limit = {
        "status": STATUS_KEY[limit_item.status] if limit_item else "no",
        "statusText": status_label(limit_item.status, lang) if limit_item else "",
        "hint": limit_item.hint if limit_item else "",
    }

    cam_state = cam_item.state if cam_item and cam_item.state else None
    wireless = (wifi_item.state if wifi_item and wifi_item.state else {}) or {}
    toggles = [
        {"id": "camera", "label": i18n.tr("toggle_camera", lang), "on": bool(cam_state and cam_state.get("enabled")),
         "can": bool(cam_state is not None and service and service.status is Status.OK)},
        {"id": "mic", "label": i18n.tr("toggle_mic", lang), "on": mic_muted is False, "can": mic_muted is not None},
        {"id": "wifi", "label": i18n.tr("toggle_wifi", lang), "on": bool(wireless.get("wlan")),
         "can": shutil.which("nmcli") is not None and "wlan" in wireless},
        {"id": "bluetooth", "label": i18n.tr("toggle_bluetooth", lang), "on": bool(wireless.get("bluetooth")),
         "can": shutil.which("bluetoothctl") is not None and "bluetooth" in wireless},
    ]

    features = []
    for i in result.items:
        f_name, f_detail, f_hint = localize_item(i, lang)
        features.append({
            "id": i.id, "name": f_name, "status": STATUS_KEY[i.status],
            "statusText": status_label(i.status, lang),
            "detail": f_detail or "", "hint": f_hint or "",
            "fix": " ".join(FIX_PACKAGES.get(i.id, [])) if i.status is not Status.OK else "",
        })
    order = {"setup": 0, "root": 1, "no": 2, "ok": 3}
    features.sort(key=lambda f: order[f["status"]])
    counts = []
    for status in (Status.OK, Status.NEEDS_SETUP, Status.NEEDS_ROOT, Status.UNAVAILABLE):
        n = sum(1 for i in result.items if i.status is status)
        if n:
            counts.append({"status": STATUS_KEY[status], "text": f"{status_label(status, lang)}: {n}"})

    return {
        "ready": True,
        "model": short_model(result.system),
        "service": bool(service and service.status is Status.OK),
        "okCount": sum(1 for i in result.items if i.status is Status.OK),
        "total": len(result.items),
        "modes": modes_for_lang(lang, has_dynamic=has_dynamic),
        "currentMode": current_mode or "",
        "scenarios": scenarios,
        "scenario": scenario,
        "cpu": {
            "name": cpu_name,
            "freq": num(cpu["freq_mhz"] / 1000, 1) if cpu.get("freq_mhz") else "—",
            "load": cpu.get("load_pct"),
            "temp": num(temp, 0),
            "fan": num(fan) if fan is not None else i18n.tr("no_data_lower", lang),
            "fanUnit": i18n.tr("unit_rpm", lang) if fan is not None else "",
        },
        "gpu": gpu,
        "battery": battery,
        "limit": limit,
        "toggles": toggles,
        "features": features,
        "counts": counts,
        "temps": temperatures(sensors.state if sensors else None, lang),
        "fans": [{"name": k.split("/", 1)[0], "rpm": v} for k, v in
                 ((sensors.state or {}).get("fans_rpm", {}) if sensors else {}).items()],
        "peripherals": [
            {"name": p.name, "kind": kind_label(p.kind, lang), "usbId": p.usb_id, "known": p.known,
             "notes": p.notes or "", "status": p.status}
            for p in result.peripherals
        ],
        "backlight": [d["name"] for d in ((kbd_item.state or {}).get("devices") or [])] if (kbd_item and kbd_item.state) else _keyboard_leds(),
        "kbdBacklight": kbd_backlight_view(kbd_item.state if kbd_item else None, bool(service and service.status is Status.OK), kbd_saved),
        "system": dict(result.system),
        "cpuHistory": list(cpu_history),
        "gpuHistory": list(gpu_history),
    }


# ---------- profiles page ----------

MODE_BY_ID = {m["id"]: m["name"] for m in MODES}

_KIND_KEYS = {
    "mouse": "kind_mouse",
    "keyboard": "kind_keyboard",
    "headset": "kind_headset",
    "camera": "kind_camera",
    "bluetooth": "kind_bluetooth",
    "laptop": "kind_laptop",
}

_BUILTIN_PROFILE_NAMES = {
    "games": {"игры", "games", "ігри", ""},
    "work": {"работа", "work", "робота", ""},
    "night": {"ночь", "night", "ніч", ""},
}

_COMMON_PROFILE_NAMES = {
    "игры": "prof_name_games", "games": "prof_name_games", "ігри": "prof_name_games",
    "работа": "prof_name_work", "work": "prof_name_work", "робота": "prof_name_work",
    "ночь": "prof_name_night", "night": "prof_name_night", "ніч": "prof_name_night",
    "кино": "prof_name_movie", "фильм": "prof_name_movie", "фильмы": "prof_name_movie",
    "movie": "prof_name_movie", "movies": "prof_name_movie", "cinema": "prof_name_movie",
    "кіно": "prof_name_movie", "фільм": "prof_name_movie", "фільми": "prof_name_movie",
    "учёба": "prof_name_study", "учеба": "prof_name_study", "study": "prof_name_study", "навчання": "prof_name_study",
    "музыка": "prof_name_music", "music": "prof_name_music", "музика": "prof_name_music",
    "стрим": "prof_name_stream", "stream": "prof_name_stream", "стрім": "prof_name_stream",
    "тишина": "prof_name_quiet", "тихий": "prof_name_quiet", "quiet": "prof_name_quiet",
    "silent": "prof_name_quiet", "тиша": "prof_name_quiet",
    "баланс": "prof_name_balanced", "balanced": "prof_name_balanced",
    "производительность": "prof_name_performance", "performance": "prof_name_performance",
    "продуктивність": "prof_name_performance",
    "батарея": "prof_name_power_saver", "энергосбережение": "prof_name_power_saver",
    "battery": "prof_name_power_saver", "power saver": "prof_name_power_saver",
    "power saving": "prof_name_power_saver", "економія": "prof_name_power_saver",
    "енергозбереження": "prof_name_power_saver",
    "офис": "prof_name_office", "office": "prof_name_office", "офіс": "prof_name_office",
    "кодинг": "prof_name_coding", "код": "prof_name_coding", "программирование": "prof_name_coding",
    "coding": "prof_name_coding", "programming": "prof_name_coding", "програмування": "prof_name_coding",
    "сон": "prof_name_sleep", "sleep": "prof_name_sleep",
    "дорога": "prof_name_travel", "travel": "prof_name_travel", "подорож": "prof_name_travel",
    "видео": "prof_name_video", "video": "prof_name_video", "відео": "prof_name_video",
    "монтаж": "prof_name_editing", "editing": "prof_name_editing",
}


def kind_label(kind: str, lang: str = "ru") -> str:
    key = _KIND_KEYS.get(kind)
    return i18n.tr(key, lang) if key else KIND_RU.get(kind, kind)


def profile_display_name(profile, lang: str = "ru") -> str:
    """Translate built-in and common custom profile names into the selected UI language."""
    pid = getattr(profile, "id", "")
    raw = str(getattr(profile, "name", "") or "").strip()
    low = raw.lower()
    if pid in _BUILTIN_PROFILE_NAMES and low in _BUILTIN_PROFILE_NAMES[pid]:
        return i18n.tr(f"prof_name_{pid}", lang)
    key = _COMMON_PROFILE_NAMES.get(low)
    if key:
        return i18n.tr(key, lang)
    return raw or pid


def _rule_edit(rule) -> dict:
    if rule is None:
        return {"processes": [], "when": "", "idle": 0, "temp": 0, "hours": ""}
    return {"processes": list(rule.processes), "when": rule.when, "idle": rule.idle,
            "temp": rule.temp, "hours": rule.hours}


def _rule_text(rule, lang: str = "ru") -> str:
    parts = []
    if rule.processes:
        parts.append(i18n.tr("rule_running", lang, procs=", ".join(rule.processes)))
    if rule.when == "battery":
        parts.append(i18n.tr("rule_on_battery", lang))
    elif rule.when == "ac":
        parts.append(i18n.tr("rule_on_ac", lang))
    return i18n.tr("rule_and", lang).join(parts)


def _plural_ru(n: int, one: str, few: str, many: str) -> str:
    n100 = abs(n) % 100
    n10 = n100 % 10
    if 11 <= n100 <= 14:
        return f"{n} {many}"
    if n10 == 1:
        return f"{n} {one}"
    if 2 <= n10 <= 4:
        return f"{n} {few}"
    return f"{n} {many}"


def _count_label(n: int, kind: str, lang: str) -> str:
    if lang == "en":
        if kind == "settings":
            return f"{n} setting" if n == 1 else f"{n} settings"
        return f"{n} rule" if n == 1 else f"{n} rules"
    if lang == "uk":
        if kind == "settings":
            return _plural_ru(n, "налаштування", "налаштування", "налаштувань")
        return _plural_ru(n, "правило", "правила", "правил")
    if kind == "settings":
        return _plural_ru(n, "настройка", "настройки", "настроек")
    return _plural_ru(n, "правило", "правила", "правил")


def profile_cards(profiles: dict, rules: list, fallback: str | None = None, lang: str = "ru") -> list[dict]:
    """One dict per profile: what it applies and which rules switch to it."""
    mode_by_id = {m["id"]: m["name"] for m in modes_for_lang(lang, has_dynamic=True)}
    unchanged = i18n.tr("unchanged", lang)
    cards = []
    for p in profiles.values():
        if lang == "ru":
            camera = "Не меняется" if p.camera is None else ("Включена" if p.camera else "Выключена")
            rows = [
                {"label": "Режим мощности", "value": mode_by_id.get(p.power or "", "Не меняется")},
                {"label": "Камера", "value": camera},
                {"label": "Звук (вывод)", "value": f"«{p.output}»" if p.output else "Не меняется"},
                {"label": "Микрофон", "value": f"«{p.input}»" if p.input else "Не меняется"},
                {"label": "Яркость", "value": f"{p.brightness} %" if p.brightness else "Не меняется"},
                {"label": "Частота экрана", "value": f"{p.refresh} Гц" if p.refresh else "Не меняется"},
            ]
        else:
            camera = unchanged if p.camera is None else i18n.tr("cam_on" if p.camera else "cam_off", lang)
            rows = [
                {"label": i18n.tr("power_mode", lang), "value": mode_by_id.get(p.power or "", unchanged)},
                {"label": i18n.tr("camera", lang), "value": camera},
                {"label": i18n.tr("sound_output", lang), "value": f"«{p.output}»" if p.output else unchanged},
                {"label": i18n.tr("microphone", lang), "value": f"«{p.input}»" if p.input else unchanged},
                {"label": i18n.tr("screen_brightness", lang), "value": f"{p.brightness} %" if p.brightness else unchanged},
                {"label": i18n.tr("screen_refresh", lang), "value": f"{p.refresh} {i18n.tr('unit_hz', lang)}" if p.refresh else unchanged},
            ]
        rule_obj = next((r for r in rules if r.profile == p.id), None)
        rule_edit = _rule_edit(rule_obj)
        settings_count = sum([
            bool(p.power),
            p.camera is not None,
            bool(p.output),
            bool(p.input),
            bool(p.brightness),
            bool(p.refresh),
        ])
        rules_count = sum([
            bool(rule_edit["processes"]),
            bool(rule_edit["when"]),
            bool(rule_edit["idle"]),
            bool(rule_edit["temp"]),
            bool(rule_edit["hours"]),
        ])
        summary_parts = []
        if settings_count:
            summary_parts.append(_count_label(settings_count, "settings", lang))
        if rules_count:
            summary_parts.append(_count_label(rules_count, "rules", lang))
        summary = " · ".join(summary_parts) if summary_parts else i18n.tr("prof_not_configured", lang)
        mode_name = mode_by_id.get(p.power or "", i18n.tr("prof_no_changes", lang))
        cards.append({
            "id": p.id,
            "name": profile_display_name(p, lang),
            "custom": p.id not in DEFAULT_PROFILES,
            "sub": i18n.tr("prof_sub_mode", lang, mode=mode_name),
            "summary": summary,
            "settingsCount": settings_count,
            "rulesCount": rules_count,
            "rows": rows,
            "rules": [_rule_text(r, lang) for r in rules if r.profile == p.id and _rule_text(r, lang)],
            "rule": rule_edit,
            "edit": {
                "power": p.power or "keep",
                "camera": "keep" if p.camera is None else ("on" if p.camera else "off"),
                "output": p.output or "",
                "input": p.input or "",
                "brightness": p.brightness or 0,
                "refresh": p.refresh or 0,
            },
        })
    return cards
