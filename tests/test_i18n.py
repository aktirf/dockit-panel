import json
import re
from pathlib import Path

from dockit.core import i18n, profiles as pf
from dockit.core.scanner import ScanItem, ScanResult
from dockit.core.status import Status
from dockit.gui import tray, viewmodel as vm


def test_all_locales_have_matching_non_empty_keys():
    base = json.loads((i18n.LOCALES_DIR / "ru.json").read_text(encoding="utf-8"))
    assert base
    for lang in i18n.SUPPORTED:
        data = json.loads((i18n.LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))
        assert set(data.keys()) == set(base.keys()), f"key mismatch in {lang}.json"
        for k, v in data.items():
            assert isinstance(v, str) and v.strip() != "", f"empty translation {lang}.{k}"


def test_every_qml_tr_key_exists_in_all_locales():
    qml_dir = Path(__file__).resolve().parents[1] / "src/dockit/gui/qml"
    ru = i18n.load_catalog("ru")
    pattern = re.compile(r'Theme\.tr\(\s*"([^"]+)"\s*\)')
    used = set()
    for path in sorted(qml_dir.glob("*.qml")):
        for key in pattern.findall(path.read_text(encoding="utf-8")):
            used.add(key)
            assert key in ru, f"missing key {key!r} used in {path.name}"
    assert len(used) > 50


def test_detect_system_lang():
    assert i18n.detect_system_lang({"LANG": "uk_UA.UTF-8"}) == "uk"
    assert i18n.detect_system_lang({"LANG": "ru_RU.UTF-8"}) == "ru"
    assert i18n.detect_system_lang({"LANG": "en_US.UTF-8"}) == "en"
    assert i18n.detect_system_lang({"LANG": "de_DE.UTF-8"}) == "en"
    assert i18n.detect_system_lang({"LC_ALL": "uk_UA.UTF-8", "LANG": "en_US.UTF-8"}) == "uk"
    assert i18n.detect_system_lang({"LANG": "C"}) == "ru"
    assert i18n.resolve_lang("en", {"LANG": "uk_UA.UTF-8"}) == "en"
    assert i18n.resolve_lang("auto", {"LANG": "uk_UA.UTF-8"}) == "uk"


def test_viewmodel_and_tray_localize_en_and_uk():
    res = ScanResult(
        system={"vendor": "GIGABYTE", "model": "GIGABYTE GAMING A16 3VH"},
        items=[
            ScanItem("service", "Service", "x", Status.OK, "ok"),
            ScanItem("sensors", "Sensors", "hwmon", Status.OK, "ok",
                     state={"temps_c": {"k10temp/temp1_input": 45.0}, "fans_rpm": {}}),
            ScanItem("gpu_nvidia", "GPU", "smi", Status.OK, "ok",
                     state={"name": "RTX", "asleep": True,
                            "sleep": {"asleep": True, "runtime": "suspended", "control": "auto", "users": []}}),
            ScanItem("battery", "Battery", "ps", Status.OK, "ok",
                     state={"batteries": [{"percent": 80, "status": "Discharging", "power_w": 15.0,
                                           "energy_wh": 45.0, "energy_full_wh": 76.0, "health_pct": 99.0, "cycles": 5}],
                            "ac_online": False}),
        ],
    )
    en = vm.build(res, "balanced", {"load_pct": 10, "freq_mhz": 3200}, "Ryzen", [], [], False, [], "", lang="en")
    assert en["modes"][0]["name"] == "Quiet"
    assert en["battery"]["text"] == "Discharging"
    assert en["battery"]["source"] == "On battery"
    assert "remaining" in en["battery"]["left"]
    assert en["gpu"]["sleepText"] == "asleep"
    assert en["temps"][0]["name"] == "Processor"

    uk = vm.build(res, "balanced", {"load_pct": 10, "freq_mhz": 3200}, "Ryzen", [], [], False, [], "", lang="uk")
    assert uk["modes"][2]["name"] == "Продуктивність"
    assert uk["battery"]["source"] == "Від батареї"
    assert uk["gpu"]["sleepText"] == "спить"

    cards_en = vm.profile_cards({"g": pf.Profile("g", "Games", power="performance")}, [pf.Rule("g", ["cs2"])], lang="en")
    assert cards_en[0]["summary"] == "1 setting · 1 rule"

    tip_en = tray.format_tooltip(en, {m["id"]: m["name"] for m in en["modes"]}, lang="en")
    assert tip_en == "DOCKIT · Balanced · CPU 45 °C · GPU asleep"
    tip_uk = tray.format_tooltip(uk, {m["id"]: m["name"] for m in uk["modes"]}, lang="uk")
    assert tip_uk == "DOCKIT · Баланс · CPU 45 °C · GPU спить"


def test_diagnostics_and_report_localize_across_all_languages():
    from dockit.core.scanner import format_report

    res = ScanResult(
        system={"vendor": "GIGABYTE", "model": "GIGABYTE GAMING A16 3VH", "kernel": "7.3.5"},
        items=[
            ScanItem("service", "Фоновая служба DOCKIT", "dockit.service", Status.OK, "ok"),
            ScanItem("battery_limit", "Лимит заряда батареи", "power_supply", Status.UNAVAILABLE,
                     "no", hint="Обновите ядро"),
            ScanItem("gpu_nvidia", "Видеокарта NVIDIA", "nvidia-smi", Status.OK, "ok",
                     state={"name": "NVIDIA RTX 5060", "asleep": False}),
            ScanItem("battery", "Батарея", "power_supply", Status.OK, "ok",
                     state={"batteries": [{"percent": 96, "status": "Not charging"}]}),
            ScanItem("audio", "Звук", "pactl", Status.OK, "ok",
                     state=[{"kind": "output", "description": "EPOS H3PRO", "default": True},
                            {"kind": "input", "description": "Mic", "default": True}]),
            ScanItem("kbd_backlight", "Подсветка клавиатуры", "hid", Status.OK, "ok",
                     state={"devices": [{"name": "GIGABYTE Keyboard", "rgb": True}]}),
        ],
    )

    rep_en = format_report(res, lang="en")
    assert "[Unavailable] Battery charge limit" in rep_en
    assert "How to fix: Update the kernel" in rep_en
    assert "[Working] NVIDIA GPU" in rep_en and "NVIDIA RTX 5060: data available." in rep_en
    assert "Charge 96%, not charging." in rep_en
    assert "Outputs: 1, microphones: 1. Current output: EPOS H3PRO." in rep_en
    assert "GIGABYTE Keyboard (HID LampArray RGB)." in rep_en
    assert "Как исправить" not in rep_en

    rep_uk = format_report(res, lang="uk")
    assert "[Недоступно] Ліміт заряду батареї" in rep_uk
    assert "Як виправити:" in rep_uk
    assert "[Працює] Відеокарта NVIDIA" in rep_uk

    rep_ru = format_report(res, lang="ru")
    assert "[Недоступно] Лимит заряда батареи" in rep_ru
    assert "Как исправить:" in rep_ru

    built_en = vm.build(res, "balanced", {"load_pct": 5, "freq_mhz": 3000}, "Ryzen", [], [], False, [], "", lang="en")
    feat_by_id = {f["id"]: f for f in built_en["features"]}
    assert feat_by_id["battery_limit"]["name"] == "Battery charge limit"
    assert "Update the kernel" in feat_by_id["battery_limit"]["hint"]
    assert feat_by_id["kbd_backlight"]["name"] == "Keyboard backlight"
