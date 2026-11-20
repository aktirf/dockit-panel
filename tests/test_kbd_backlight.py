import struct
from pathlib import Path

import pytest

from dockit.core import kbd_backlight as kb
from dockit.daemon import actions
from dockit.gui import viewmodel as vm

# Real 327-byte HID LampArray descriptor captured from Gigabyte Gaming A16 (0414:8104.000A)
GIGABYTE_A16_DESCRIPTOR = bytes.fromhex(
    "05 59 09 01 a1 01 85 01 09 02 a1 02 09 03 15 00 27 ff ff 00 00 75 10 95 01 b1 03"
    " 09 04 09 05 09 06 09 07 09 08 15 00 27 ff ff ff 7f 75 20 95 05 b1 03 c0"
    " 85 02 09 20 a1 02 09 21 15 00 27 ff ff 00 00 75 10 95 01 b1 02 c0"
    " 85 03 09 22 a1 02 09 21 15 00 27 ff ff 00 00 75 10 95 01 b1 02"
    " 09 23 09 24 09 25 09 27 09 26 15 00 27 ff ff ff 7f 75 20 95 05 b1 02"
    " 09 28 09 29 09 2a 09 2b 09 2c 09 2d 15 00 26 ff 00 75 08 95 06 b1 02 c0"
    " 85 04 09 50 a1 02 09 03 09 55 15 00 25 08 75 08 95 02 b1 02"
    " 09 21 15 00 27 ff ff 00 00 75 10 95 08 b1 02"
    " 09 51 09 52 09 53 09 54 09 51 09 52 09 53 09 54"
    " 09 51 09 52 09 53 09 54 09 51 09 52 09 53 09 54"
    " 09 51 09 52 09 53 09 54 09 51 09 52 09 53 09 54"
    " 09 51 09 52 09 53 09 54 09 51 09 52 09 53 09 54"
    " 15 00 26 ff 00 75 08 95 20 b1 02 c0"
    " 85 05 09 60 a1 02 09 55 15 00 25 08 75 08 95 01 b1 02"
    " 09 61 09 62 15 00 27 ff ff 00 00 75 10 95 02 b1 02"
    " 09 51 09 52 09 53 09 54 15 00 26 ff 00 75 08 95 04 b1 02 c0"
    " 85 06 09 70 a1 02 09 71 15 00 25 01 75 08 95 01 b1 02 c0 c0"
)

# Standard boot keyboard descriptor (Usage Page 0x01, Usage 0x06)
STANDARD_KBD_DESCRIPTOR = bytes.fromhex(
    "05 01 09 06 a1 01 05 08 15 00 25 01 19 01 29 03 75 01 95 03 91 02 c0"
)


# ---------- descriptor & packet parsing ----------

def test_parse_gigabyte_a16_lamparray_descriptor():
    ids = kb.parse_lamparray_descriptor(GIGABYTE_A16_DESCRIPTOR)
    assert ids == {"attributes_id": 1, "range_update_id": 5, "control_id": 6}


def test_parse_custom_report_ids_lamparray():
    custom = bytes.fromhex(
        "05 59 09 01 a1 01"
        " 85 11 09 02 a1 02 c0"
        " 85 15 09 60 a1 02 c0"
        " 85 16 09 70 a1 02 c0"
        " c0"
    )
    assert kb.parse_lamparray_descriptor(custom) == {
        "attributes_id": 0x11,
        "range_update_id": 0x15,
        "control_id": 0x16,
    }


@pytest.mark.parametrize("bad", [b"", STANDARD_KBD_DESCRIPTOR, b"\x05\x59\x09\x01\xa1", b"\xfe\x02\x00\x01"])
def test_parse_non_lamparray_returns_none(bad):
    assert kb.parse_lamparray_descriptor(bad) is None


def test_parse_hid_uevent():
    text = (
        "DRIVER=hid-generic\n"
        "HID_ID=0003:00000414:00008104\n"
        "HID_NAME=GIGABYTE USB-HID Keyboard\n"
    )
    assert kb.parse_hid_uevent(text) == {
        "name": "GIGABYTE USB-HID Keyboard",
        "usb_id": "0414:8104",
    }


def test_parse_and_normalize_hex_color():
    assert kb.parse_hex_color("#5ab0ff") == (0x5A, 0xB0, 0xFF)
    assert kb.normalize_hex_color("#5ab0ff") == "#5AB0FF"
    for bad in ("5AB0FF", "#5AB0F", "#5AB0FF00", "#GGGGGG", "", None, 123):
        with pytest.raises(ValueError):
            kb.parse_hex_color(bad)  # type: ignore[arg-type]


def test_build_control_report():
    assert kb.build_control_report(False, 6) == b"\x06\x00"
    assert kb.build_control_report(True, 6) == b"\x06\x01"


def test_build_range_update_report_scaling():
    # Full brightness white across 104 lamps
    pkt = kb.build_range_update_report(104, 255, 255, 255, 100, report_id=5)
    assert len(pkt) == 10
    rid, flags, start, end, r, g, b, intensity = struct.unpack("<BBHHBBBB", pkt)
    assert (rid, flags, start, end) == (5, 1, 0, 103)
    assert (r, g, b, intensity) == (255, 255, 255, 255)

    # 50% brightness scales RGB channels proportionally
    pkt50 = kb.build_range_update_report(1, 200, 100, 50, 50)
    _, _, start, end, r, g, b, intensity = struct.unpack("<BBHHBBBB", pkt50)
    assert (start, end, r, g, b, intensity) == (0, 0, 100, 50, 25, 255)

    # 1% brightness keeps non-black color faintly visible instead of rounding to 0
    pkt1 = kb.build_range_update_report(1, 10, 0, 0, 1)
    _, _, _, _, r, g, b, intensity = struct.unpack("<BBHHBBBB", pkt1)
    assert (r, g, b, intensity) == (1, 0, 0, 255)

    # 0% turns off RGB and intensity
    pkt0 = kb.build_range_update_report(10, 255, 255, 255, 0)
    _, _, _, _, r, g, b, intensity = struct.unpack("<BBHHBBBB", pkt0)
    assert (r, g, b, intensity) == (0, 0, 0, 0)


def test_parse_attributes_report():
    raw = struct.pack("<BHIIIII", 1, 104, 300000, 120000, 10000, 1, 33000)
    parsed = kb.parse_attributes_report(raw)
    assert parsed is not None
    assert parsed["lamp_count"] == 104
    assert parsed["kind"] == 1
    assert kb.parse_attributes_report(b"\x01") is None


# ---------- discovery & daemon actions ----------

def _make_lamparray_sysfs(tmp_path: Path, hidraw_name: str = "hidraw9"):
    hid_base = tmp_path / "hid"
    dev_dir = hid_base / "0003:0414:8104.000A"
    (dev_dir / "hidraw" / hidraw_name).mkdir(parents=True)
    (dev_dir / "report_descriptor").write_bytes(GIGABYTE_A16_DESCRIPTOR)
    (dev_dir / "uevent").write_text(
        "HID_ID=0003:00000414:00008104\nHID_NAME=GIGABYTE USB-HID Keyboard\n"
    )
    # Non-LampArray sibling should be ignored
    other = hid_base / "0003:0414:8104.0004"
    (other / "hidraw" / "hidraw0").mkdir(parents=True)
    (other / "report_descriptor").write_bytes(STANDARD_KBD_DESCRIPTOR)
    (other / "uevent").write_text("HID_NAME=Regular Keyboard\n")

    dev_base = tmp_path / "dev"
    dev_base.mkdir()
    (dev_base / hidraw_name).write_bytes(b"")
    return str(hid_base), str(dev_base)


def _make_led_sysfs(tmp_path: Path, brightness: int = 2, max_brightness: int = 3):
    leds = tmp_path / "leds"
    d = leds / "asus::kbd_backlight"
    d.mkdir(parents=True)
    (d / "brightness").write_text(f"{brightness}\n")
    (d / "max_brightness").write_text(f"{max_brightness}\n")
    # Unrelated capslock LED must be ignored
    caps = leds / "input2::capslock"
    caps.mkdir(parents=True)
    (caps / "brightness").write_text("0\n")
    (caps / "max_brightness").write_text("1\n")
    return str(leds)


def test_discover_lamparray_and_leds(tmp_path):
    hid_base, _ = _make_lamparray_sysfs(tmp_path)
    leds_base = _make_led_sysfs(tmp_path, 2, 4)

    devs = kb.discover(hid_base, leds_base)
    assert len(devs) == 2
    assert devs[0]["backend"] == "lamparray"
    assert devs[0]["rgb"] is True
    assert devs[0]["usb_id"] == "0414:8104"
    assert devs[1]["backend"] == "led"
    assert devs[1]["rgb"] is False
    assert devs[1]["brightness"] == 50


def test_action_set_kbd_backlight_lamparray_rgb(tmp_path):
    hid_base, dev_base = _make_lamparray_sysfs(tmp_path)
    calls = []

    def fake_ioctl(fd, req, buf):
        calls.append((req, bytes(buf)))
        if req == kb._hidioc_gfeature(23):
            # Populate LampCount = 4
            buf[:] = struct.pack("<BHIIIII", 1, 4, 0, 0, 0, 1, 0)
        return buf

    result = actions.set_kbd_backlight(
        {"on": True, "brightness": 50, "color": "#5ab0ff", "autonomous": False},
        hid_base=hid_base,
        leds_base=str(tmp_path / "no-leds"),
        dev_base=dev_base,
        ioctl_fn=fake_ioctl,
    )
    assert result["backend"] == "lamparray"
    assert result["color"] == "#5AB0FF"
    assert result["lamps"] == 4
    assert result["on"] is True
    assert result["autonomous"] is False
    assert len(calls) == 3
    # 1: GET attributes, 2: SET control(0), 3: SET range_update(0..3, scaled RGB)
    assert calls[1][1] == b"\x06\x00"
    rid, flags, start, end, r, g, b, intensity = struct.unpack("<BBHHBBBB", calls[2][1])
    assert (rid, flags, start, end, intensity) == (5, 1, 0, 3, 255)
    assert (r, g, b) == (45, 88, 128)


def test_action_set_kbd_backlight_lamparray_autonomous(tmp_path):
    hid_base, dev_base = _make_lamparray_sysfs(tmp_path)
    calls = []

    def fake_ioctl(fd, req, buf):
        calls.append((req, bytes(buf)))
        return buf

    result = actions.set_kbd_backlight(
        {"on": True, "brightness": 100, "color": "#FFFFFF", "autonomous": True},
        hid_base=hid_base,
        leds_base=str(tmp_path / "no-leds"),
        dev_base=dev_base,
        ioctl_fn=fake_ioctl,
    )
    assert result["autonomous"] is True
    assert len(calls) == 1
    assert calls[0][1] == b"\x06\x01"


def test_action_set_kbd_backlight_led_write(tmp_path):
    leds_base = _make_led_sysfs(tmp_path, 0, 4)
    res = actions.set_kbd_backlight(
        {"on": True, "brightness": 50},
        hid_base=str(tmp_path / "no-hid"),
        leds_base=leds_base,
    )
    assert res["backend"] == "led"
    assert res["brightness"] == 50
    assert (Path(leds_base) / "asus::kbd_backlight" / "brightness").read_text() == "2"

    res_off = actions.set_kbd_backlight(
        {"on": False, "brightness": 80},
        hid_base=str(tmp_path / "no-hid"),
        leds_base=leds_base,
    )
    assert res_off["on"] is False
    assert (Path(leds_base) / "asus::kbd_backlight" / "brightness").read_text() == "0"


@pytest.mark.parametrize("bad", [
    "on",
    None,
    {"on": "yes"},
    {"autonomous": 1},
    {"brightness": True},
    {"brightness": -1},
    {"brightness": 101},
    {"color": "blue"},
    {"color": "#12345"},
])
def test_action_set_kbd_backlight_rejects_bad_input(tmp_path, bad):
    leds_base = _make_led_sysfs(tmp_path, 1, 3)
    with pytest.raises(actions.ActionError):
        actions.set_kbd_backlight(bad, hid_base=str(tmp_path / "no-hid"), leds_base=leds_base)


def test_action_set_kbd_backlight_no_hardware(tmp_path):
    with pytest.raises(actions.ActionError):
        actions.set_kbd_backlight(
            {"on": True, "brightness": 80, "color": "#FFFFFF"},
            hid_base=str(tmp_path / "no-hid"),
            leds_base=str(tmp_path / "no-leds"),
        )


# ---------- viewmodel ----------

def test_viewmodel_kbd_backlight_view():
    empty = vm.kbd_backlight_view(None, True)
    assert empty["available"] is False and empty["can"] is False

    rgb_state = {
        "devices": [{"id": "0003:0414:8104.000A", "name": "GIGABYTE", "backend": "lamparray", "rgb": True, "brightness": None}]
    }
    view = vm.kbd_backlight_view(rgb_state, True, {"on": True, "brightness": 70, "color": "#4CC38A", "autonomous": False})
    assert view["available"] is True and view["can"] is True and view["rgb"] is True
    assert view["brightness"] == 70 and view["color"] == "#4CC38A"

    # Without daemon, can is False
    assert vm.kbd_backlight_view(rgb_state, False)["can"] is False

    # LED backend reads live sysfs brightness
    led_state = {
        "devices": [{"id": "asus::kbd_backlight", "name": "asus::kbd_backlight", "backend": "led", "rgb": False, "brightness": 33}]
    }
    led_view = vm.kbd_backlight_view(led_state, True)
    assert led_view["rgb"] is False and led_view["brightness"] == 33 and led_view["on"] is True
