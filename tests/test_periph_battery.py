from pathlib import Path

from dockit.core import periph_battery as pb
from dockit.gui import viewmodel as vm


SAMPLE_UPOWER = """
Device: /org/freedesktop/UPower/devices/line_power_ACAD
  native-path:          ACAD
  power supply:         yes
  online:               yes

Device: /org/freedesktop/UPower/devices/battery_BAT1
  native-path:          BAT1
  vendor:               COSMX40
  model:                GAD-640
  power supply:         yes
  present:              yes
  state:                fully-charged
  percentage:           96%

Device: /org/freedesktop/UPower/devices/mouse_hidpp_battery_0
  native-path:          hidpp_battery_0
  vendor:               Logitech
  model:                G PRO X SUPERLIGHT
  serial:               aa-bb-cc-dd
  power supply:         no
  present:              yes
  mouse
    state:              discharging
    percentage:         78%
    icon-name:          'battery-good-symbolic'

Device: /org/freedesktop/UPower/devices/headset_dev_AA_BB_CC_DD_EE_FF
  native-path:          /org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF
  model:                EPOS H3PRO Hybrid
  serial:               AA:BB:CC:DD:EE:FF
  power supply:         no
  present:              yes
  headset
    state:              charging
    percentage:         62%
    icon-name:          'audio-headset-symbolic'

Device: /org/freedesktop/UPower/devices/keyboard_absent
  native-path:          hidpp_battery_1
  model:                Offline Keyboard
  power supply:         no
  present:              no
  keyboard
    percentage:         50%

Device: /org/freedesktop/UPower/devices/DisplayDevice
  power supply:         yes
  state:                fully-charged
  percentage:           96%
"""


def test_parse_upower_filters_laptop_and_keeps_peripherals():
    items = pb.parse_upower(SAMPLE_UPOWER)
    assert len(items) == 2
    mouse, headset = items

    assert mouse.name == "Logitech G PRO X SUPERLIGHT"
    assert mouse.percent == 78
    assert mouse.status == "discharging"
    assert mouse.kind == "mouse"
    assert mouse.source == "upower"

    assert headset.name == "EPOS H3PRO Hybrid"
    assert headset.percent == 62
    assert headset.status == "charging"
    assert headset.kind == "headset"
    assert headset.key == "aabbccddeeff"


def test_read_sysfs_batteries(tmp_path: Path):
    # Laptop main battery (must be skipped)
    bat = tmp_path / "BAT1"
    bat.mkdir()
    (bat / "type").write_text("Battery\n")
    (bat / "capacity").write_text("95\n")

    # USB-C UCSI port (scope=Device, type=USB -> must be skipped)
    ucsi = tmp_path / "ucsi-source-psy-USBC000:001"
    ucsi.mkdir()
    (ucsi / "type").write_text("USB\n")
    (ucsi / "scope").write_text("Device\n")

    # Wireless mouse (HID++)
    mouse = tmp_path / "hidpp_battery_0"
    mouse.mkdir()
    (mouse / "type").write_text("Battery\n")
    (mouse / "scope").write_text("Device\n")
    (mouse / "manufacturer").write_text("Logitech\n")
    (mouse / "model_name").write_text("MX Master 3S\n")
    (mouse / "serial_number").write_text("aa-bb-cc-dd\n")
    (mouse / "capacity").write_text("85\n")
    (mouse / "status").write_text("Discharging\n")

    # Coarse-level-only device (no capacity file)
    kbd = tmp_path / "hidpp_battery_1"
    kbd.mkdir()
    (kbd / "type").write_text("Battery\n")
    (kbd / "scope").write_text("Device\n")
    (kbd / "model_name").write_text("Logitech Wireless Keyboard\n")
    (kbd / "capacity_level").write_text("High\n")
    (kbd / "status").write_text("Unknown\n")

    items = pb.read_sysfs_batteries(str(tmp_path))
    assert len(items) == 2
    assert items[0].name == "Logitech MX Master 3S"
    assert items[0].percent == 85
    assert items[0].kind == "mouse"
    assert items[1].name == "Logitech Wireless Keyboard"
    assert items[1].percent is None
    assert items[1].level == "High"
    assert items[1].kind == "keyboard"


def test_parse_headsetcontrol_json_and_legacy():
    js = """{
      "devices": [
        {"device": "SteelSeries Arctis Nova 7", "battery": {"status": "BATTERY_AVAILABLE", "level": 74}},
        {"device": "Corsair HS80", "battery": {"status": "BATTERY_CHARGING", "level": 90}},
        {"device": "Offline Headset", "battery": {"status": "BATTERY_UNAVAILABLE", "level": -1}}
      ]
    }"""
    items = pb.parse_headsetcontrol(js)
    assert len(items) == 2
    assert items[0].name == "SteelSeries Arctis Nova 7" and items[0].percent == 74 and items[0].status == "discharging"
    assert items[1].name == "Corsair HS80" and items[1].percent == 90 and items[1].status == "charging"

    legacy = "Found HyperX Cloud II Wireless!\nBattery: 65%\n"
    legacy_items = pb.parse_headsetcontrol(legacy)
    assert len(legacy_items) == 1
    assert legacy_items[0].name == "HyperX Cloud II Wireless" and legacy_items[0].percent == 65

    assert pb.parse_headsetcontrol("Found Headset!\nBattery: Unavailable\n") == []


def test_merge_deduplicates_across_sources_and_enriches_bluetooth():
    upower_items = pb.parse_upower(SAMPLE_UPOWER)
    sysfs_dup = [
        pb.PeripheralBattery(
            name="G PRO X SUPERLIGHT",
            percent=78,
            status="unknown",
            kind="mouse",
            source="sysfs",
            key="aabbccdd",
        )
    ]
    bt_raw = [
        {"name": "EPOS H3PRO Hybrid", "battery": -1, "icon": "audio-headset"},
        {"name": "Sony WH-1000XM5", "battery": 45, "icon": "audio-headphones"},
    ]

    merged = pb.merge_batteries(upower_items, sysfs_dup, bluetooth_devices=bt_raw)
    names = [m["name"] for m in merged]
    assert len(merged) == 3
    assert "Logitech G PRO X SUPERLIGHT" in names
    assert "EPOS H3PRO Hybrid" in names
    assert "Sony WH-1000XM5" in names

    epos = next(m for m in merged if m["name"] == "EPOS H3PRO Hybrid")
    assert epos["percent"] == 62 and epos["status"] == "charging"

    enriched = pb.enrich_bluetooth(bt_raw, merged)
    assert enriched[0]["battery"] == 62
    assert enriched[1]["battery"] == 45


def test_viewmodel_periph_batteries_view_localized():
    raw = [
        {"name": "EPOS H3PRO Hybrid", "percent": 62, "status": "charging", "kind": "headset", "source": "upower", "level": ""},
        {"name": "Logitech MX Master", "percent": 80, "status": "discharging", "kind": "mouse", "source": "sysfs", "level": ""},
    ]
    ru = vm.periph_batteries_view(raw, "ru")
    en = vm.periph_batteries_view(raw, "en")
    uk = vm.periph_batteries_view(raw, "uk")

    assert ru[0]["charging"] is True and ru[0]["statusText"] == "Заряжается" and ru[0]["source"] == "UPower"
    assert en[0]["statusText"] == "Charging" and en[1]["source"] == "HID / sysfs"
    assert uk[0]["statusText"] == "Заряджається"
