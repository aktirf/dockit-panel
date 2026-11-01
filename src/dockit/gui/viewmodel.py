"""Turns scan results into plain data for the window.

No Qt here, so it can be tested without a screen. Everything returned is
simple dicts, lists, strings, numbers and booleans.
"""

from __future__ import annotations

import shutil

from ..core.scanner import ScanResult, display_name
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


def temperatures(sensors_state: dict | None) -> list[dict]:
    """The hottest reading of every chip, with a plain name."""
    best: dict[str, float] = {}
    for key, value in ((sensors_state or {}).get("temps_c") or {}).items():
        chip = key.split("/", 1)[0]
        name = CHIP_RU.get(chip, chip)
        best[name] = max(best.get(name, value), value)
    return [{"name": n, "value": f"{v:.0f}", "hot": v >= 85} for n, v in sorted(best.items())]


def _keyboard_leds() -> list[str]:
    import glob
    return [p.rsplit("/", 1)[-1] for p in glob.glob("/sys/class/leds/*kbd*")]


def _item(result: ScanResult, item_id: str):
    return next((i for i in result.items if i.id == item_id), None)


def empty() -> dict:
    return {"ready": False, "model": "", "service": False, "okCount": 0, "total": 0,
            "modes": MODES, "currentMode": "", "scenarios": [], "scenario": "",
            "cpu": {}, "gpu": {}, "battery": {}, "limit": {}, "toggles": [], "temps": [], "fans": [],
            "peripherals": [], "backlight": [], "system": {},
            "features": [], "counts": [], "cpuHistory": [], "gpuHistory": [], "profiles": [],
            "audio": {"outputs": [], "inputs": []}, "apps": [], "idleAvailable": False,
            "fallback": ""}


def build(result: ScanResult, current_mode: str | None, cpu: dict, cpu_name: str,
          cpu_history: list, gpu_history: list, mic_muted: bool | None,
          scenarios: list[dict], scenario: str) -> dict:
    service = _item(result, "service")
    sensors = _item(result, "sensors")
    gpu_item = _item(result, "gpu_nvidia")
    bat_item = _item(result, "battery")
    limit_item = _item(result, "battery_limit")
    cam_item = _item(result, "camera")
    wifi_item = _item(result, "wireless")

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
        "statusText": LABELS_RU[gpu_item.status] if gpu_item else "",
    }

    bats = ((bat_item.state if bat_item else None) or {}).get("batteries", [])
    ac = ((bat_item.state if bat_item else None) or {}).get("ac_online")
    b = bats[0] if bats else {}
    battery = {
        "percent": b.get("percent"),
        "text": BATTERY_TEXT.get(b.get("status") or "", b.get("status") or "Нет данных"),
        "source": "От сети" if ac else ("От батареи" if ac is False else ""),
        "health": num(b.get("health_pct"), 0) if b.get("health_pct") is not None else "—",
        "cycles": b.get("cycles"),
        "status": STATUS_KEY[bat_item.status] if bat_item else "no",
        "statusText": LABELS_RU[bat_item.status] if bat_item else "",
    }
    limit = {
        "status": STATUS_KEY[limit_item.status] if limit_item else "no",
        "statusText": LABELS_RU[limit_item.status] if limit_item else "",
    }

    cam_state = cam_item.state if cam_item and cam_item.state else None
    wireless = (wifi_item.state if wifi_item and wifi_item.state else {}) or {}
    toggles = [
        {"id": "camera", "label": "Веб-камера", "on": bool(cam_state and cam_state.get("enabled")),
         "can": bool(cam_state is not None and service and service.status is Status.OK)},
        {"id": "mic", "label": "Микрофон", "on": mic_muted is False, "can": mic_muted is not None},
        {"id": "wifi", "label": "Wi-Fi", "on": bool(wireless.get("wlan")), "can": shutil.which("nmcli") is not None
         and "wlan" in wireless},
        {"id": "bluetooth", "label": "Bluetooth", "on": bool(wireless.get("bluetooth")),
         "can": shutil.which("bluetoothctl") is not None and "bluetooth" in wireless},
    ]

    features = [
        {"id": i.id, "name": i.name, "status": STATUS_KEY[i.status], "statusText": LABELS_RU[i.status],
         "detail": i.detail or "", "hint": i.hint or ""}
        for i in result.items
    ]
    order = {"setup": 0, "root": 1, "no": 2, "ok": 3}
    features.sort(key=lambda f: order[f["status"]])
    counts = []
    for status in (Status.OK, Status.NEEDS_SETUP, Status.NEEDS_ROOT, Status.UNAVAILABLE):
        n = sum(1 for i in result.items if i.status is status)
        if n:
            counts.append({"status": STATUS_KEY[status], "text": f"{LABELS_RU[status]}: {n}"})

    return {
        "ready": True,
        "model": short_model(result.system),
        "service": bool(service and service.status is Status.OK),
        "okCount": sum(1 for i in result.items if i.status is Status.OK),
        "total": len(result.items),
        "modes": MODES,
        "currentMode": current_mode or "",
        "scenarios": scenarios,
        "scenario": scenario,
        "cpu": {
            "name": cpu_name,
            "freq": num(cpu["freq_mhz"] / 1000, 1) if cpu.get("freq_mhz") else "—",
            "load": cpu.get("load_pct"),
            "temp": num(temp, 0),
            "fan": num(fan) if fan is not None else "нет данных",
            "fanUnit": "об/мин" if fan is not None else "",
        },
        "gpu": gpu,
        "battery": battery,
        "limit": limit,
        "toggles": toggles,
        "features": features,
        "counts": counts,
        "temps": temperatures(sensors.state if sensors else None),
        "fans": [{"name": k.split("/", 1)[0], "rpm": v} for k, v in
                 ((sensors.state or {}).get("fans_rpm", {}) if sensors else {}).items()],
        "peripherals": [
            {"name": p.name, "kind": KIND_RU.get(p.kind, p.kind), "usbId": p.usb_id, "known": p.known,
             "notes": p.notes or "", "status": p.status}
            for p in result.peripherals
        ],
        "backlight": _keyboard_leds(),
        "system": dict(result.system),
        "cpuHistory": list(cpu_history),
        "gpuHistory": list(gpu_history),
    }


# ---------- profiles page ----------

MODE_BY_ID = {m["id"]: m["name"] for m in MODES}


def _rule_edit(rule) -> dict:
    if rule is None:
        return {"processes": [], "when": "", "idle": 0}
    return {"processes": list(rule.processes), "when": rule.when, "idle": rule.idle}


def _rule_text(rule) -> str:
    parts = []
    if rule.processes:
        parts.append("Запущена программа: " + ", ".join(rule.processes))
    if rule.when == "battery":
        parts.append("Ноутбук работает от батареи")
    elif rule.when == "ac":
        parts.append("Ноутбук подключён к зарядке")
    return " и ".join(parts)


def profile_cards(profiles: dict, rules: list, fallback: str | None = None) -> list[dict]:
    """One dict per profile: what it applies and which rules switch to it."""
    cards = []
    for p in profiles.values():
        camera = "Не меняется" if p.camera is None else ("Включена" if p.camera else "Выключена")
        rows = [
            {"label": "Режим мощности", "value": MODE_BY_ID.get(p.power or "", "Не меняется")},
            {"label": "Камера", "value": camera},
            {"label": "Звук (вывод)", "value": f"«{p.output}»" if p.output else "Не меняется"},
            {"label": "Микрофон", "value": f"«{p.input}»" if p.input else "Не меняется"},
        ]
        cards.append({
            "id": p.id,
            "name": p.name,
            "sub": "Режим: " + MODE_BY_ID.get(p.power or "", "без изменений"),
            "rows": rows,
            "rules": [_rule_text(r) for r in rules if r.profile == p.id and _rule_text(r)],
            "rule": _rule_edit(next((r for r in rules if r.profile == p.id), None)),
            "edit": {
                "power": p.power or "keep",
                "camera": "keep" if p.camera is None else ("on" if p.camera else "off"),
                "output": p.output or "",
                "input": p.input or "",
            },
        })
    return cards
