import re
from pathlib import Path

import pytest

from dockit.core import battery_limit, gpu_amd, hardware, usb
from dockit.core.scanner import ScanItem, ScanResult
from dockit.core.status import Status
from dockit.daemon import actions, protocol, server
from dockit.gui import viewmodel as vm
from dockit.modules.battery_limit import BatteryLimit


# ---------- 1. Universal UVC webcam auto-detection ----------

def _make_usb(base: Path, port: str, vendor: str, product: str, iface_class: str | None = None):
    d = base / port
    d.mkdir(parents=True)
    (d / "idVendor").write_text(vendor + "\n")
    (d / "idProduct").write_text(product + "\n")
    (d / "authorized").write_text("1\n")
    if iface_class is not None:
        iface = base / f"{port}:1.0"
        iface.mkdir()
        (iface / "bInterfaceClass").write_text(iface_class + "\n")


def test_uvc_camera_auto_detected_without_database_and_can_re_enable(tmp_path):
    usb_dir = tmp_path / "usb"
    cache = tmp_path / "uvc_cameras.json"
    _make_usb(usb_dir, "2-3", "04f2", "b751", iface_class="0e")   # random ThinkPad/ASUS UVC webcam
    _make_usb(usb_dir, "1-2", "046d", "c539", iface_class="03")   # HID mouse, must not be touched

    assert usb.is_uvc_camera(usb_dir, "2-3") is True
    assert usb.is_uvc_camera(usb_dir, "1-2") is False

    # Empty device database: UVC webcam is still detected and can be turned off!
    state = actions.set_camera(False, str(usb_dir), entries=[], uvc_cache=cache)
    assert state["cameras"] == [{"usb_id": "04f2:b751", "port": "2-3", "enabled": False}]
    assert (usb_dir / "2-3" / "authorized").read_text().strip() == "0"
    assert (usb_dir / "1-2" / "authorized").read_text().strip() == "1"

    # Simulate Linux kernel removing interface dir while authorized=0:
    (usb_dir / "2-3:1.0" / "bInterfaceClass").unlink()
    (usb_dir / "2-3:1.0").rmdir()
    assert usb.is_uvc_camera(usb_dir, "2-3") is False

    # Thanks to uvc_cache, the camera is STILL recognized and can be switched back ON!
    state_on = actions.set_camera(True, str(usb_dir), entries=[], uvc_cache=cache)
    assert state_on["cameras"] == [{"usb_id": "04f2:b751", "port": "2-3", "enabled": True}]
    assert (usb_dir / "2-3" / "authorized").read_text().strip() == "1"


# ---------- 2. Universal battery charge limit ----------

def test_battery_limit_threshold_read_and_write(tmp_path):
    ps = tmp_path / "ps"
    bat = ps / "BAT0"
    bat.mkdir(parents=True)
    (bat / "charge_control_end_threshold").write_text("100\n")

    info = battery_limit.discover(str(ps), str(tmp_path / "no_ideapad"))
    assert info["kind"] == "threshold" and info["value"] == 100

    res = actions.set_battery_limit(80, str(ps), str(tmp_path / "no_ideapad"))
    assert res == {"kind": "threshold", "value": 80, "conservation": None}
    assert (bat / "charge_control_end_threshold").read_text().strip() == "80"

    for bad in (49, 101, 0, True, "80", None):
        with pytest.raises(actions.ActionError):
            actions.set_battery_limit(bad, str(ps), str(tmp_path / "no_ideapad"))


def test_battery_limit_lenovo_conservation_mode(tmp_path):
    ideapad = tmp_path / "ideapad" / "VPC2004:00"
    ideapad.mkdir(parents=True)
    (ideapad / "conservation_mode").write_text("0\n")

    info = battery_limit.discover(str(tmp_path / "no_ps"), str(tmp_path / "ideapad"))
    assert info["kind"] == "conservation" and info["conservation"] is False and info["value"] == 100

    res = actions.set_battery_limit(80, str(tmp_path / "no_ps"), str(tmp_path / "ideapad"))
    assert res == {"kind": "conservation", "value": 80, "conservation": True}
    assert (ideapad / "conservation_mode").read_text().strip() == "1"

    res_off = actions.set_battery_limit(100, str(tmp_path / "no_ps"), str(tmp_path / "ideapad"))
    assert res_off == {"kind": "conservation", "value": 100, "conservation": False}
    assert (ideapad / "conservation_mode").read_text().strip() == "0"


def test_battery_limit_module_and_polkit_policy(tmp_path, monkeypatch):
    ps = tmp_path / "ps"
    bat = ps / "BAT0"
    bat.mkdir(parents=True)
    (bat / "charge_control_end_threshold").write_text("80\n")

    import dockit.modules.battery_limit as bl_mod
    monkeypatch.setattr(bl_mod, "daemon_running", lambda: True)
    mod = BatteryLimit(str(ps), str(tmp_path / "none"))
    assert mod.detect().status is Status.OK
    assert mod.get_state() == {"kind": "threshold", "value": 80, "conservation": None}

    assert protocol.POLKIT_IDS["set_battery_limit"] == "org.dockit.set-battery-limit"
    policy = (Path(__file__).resolve().parents[1] / "data/polkit/org.dockit.policy").read_text()
    blocks = dict(re.findall(r'<action id="([^"]+)">(.*?)</action>', policy, re.S))
    assert "org.dockit.set-battery-limit" in blocks
    assert "<allow_any>no</allow_any>" in blocks["org.dockit.set-battery-limit"]
    assert "<allow_inactive>no</allow_inactive>" in blocks["org.dockit.set-battery-limit"]

    # Dispatcher routes set_battery_limit properly
    called = []
    monkeypatch.setattr(actions, "set_battery_limit", lambda v: called.append(v) or {"kind": "threshold", "value": v, "conservation": None})
    disp = server.Dispatcher(lambda *a: (True, ""), log=lambda t: None)
    resp = disp.handle(b'{"action":"set_battery_limit","value":80}', 100, 1000)
    assert resp["ok"] is True and called == [80]


# ---------- 3. Universal AMD GPU monitoring ----------

def test_amd_gpu_sysfs_reads_discrete_over_igpu_and_handles_sleep(tmp_path):
    pci = tmp_path / "pci"
    # iGPU: boot_vga=1, 512 MB VRAM
    igpu = pci / "0000:65:00.0"
    (igpu / "hwmon" / "hwmon0").mkdir(parents=True)
    (igpu / "power").mkdir()
    (igpu / "vendor").write_text("0x1002\n")
    (igpu / "class").write_text("0x030000\n")
    (igpu / "boot_vga").write_text("1\n")
    (igpu / "gpu_busy_percent").write_text("5\n")
    (igpu / "mem_info_vram_total").write_text(str(512 * 1024 * 1024) + "\n")
    (igpu / "power" / "runtime_status").write_text("active\n")

    # Discrete Radeon GPU: boot_vga=0, 8 GB VRAM
    dgpu = pci / "0000:03:00.0"
    (dgpu / "hwmon" / "hwmon1").mkdir(parents=True)
    (dgpu / "power").mkdir()
    (dgpu / "vendor").write_text("0x1002\n")
    (dgpu / "class").write_text("0x030000\n")
    (dgpu / "boot_vga").write_text("0\n")
    (dgpu / "product_name").write_text("AMD Radeon RX 7700S\n")
    (dgpu / "gpu_busy_percent").write_text("64\n")
    (dgpu / "mem_info_vram_used").write_text(str(2048 * 1024 * 1024) + "\n")
    (dgpu / "mem_info_vram_total").write_text(str(8192 * 1024 * 1024) + "\n")
    (dgpu / "hwmon" / "hwmon1" / "temp1_input").write_text("68000\n")
    (dgpu / "hwmon" / "hwmon1" / "power1_average").write_text("72500000\n")
    (dgpu / "pp_dpm_sclk").write_text("0: 500Mhz\n1: 2150Mhz *\n2: 2400Mhz\n")
    (dgpu / "power" / "runtime_status").write_text("active\n")
    (dgpu / "power" / "control").write_text("auto\n")

    info = gpu_amd.summary(str(pci))
    assert info["name"] == "AMD Radeon RX 7700S"
    assert info["util_pct"] == 64
    assert info["temp_c"] == 68
    assert info["power_w"] == 72.5
    assert info["clock_mhz"] == 2150
    assert info["mem_used_mb"] == 2048 and info["mem_total_mb"] == 8192
    assert info["asleep"] is False

    # ViewModel & Welcome use AMD GPU cleanly when NVIDIA is absent
    res = ScanResult(
        system={"vendor": "ASUS", "model": "TUF A16 Advantage", "kernel": "6.14.0"},
        items=[
            ScanItem("service", "Service", "systemd", Status.OK, "ok"),
            ScanItem("gpu_nvidia", "NVIDIA", "smi", Status.UNAVAILABLE, "no nvidia"),
            ScanItem("battery_limit", "Limit", "ps", Status.OK, "80%",
                     state={"kind": "threshold", "value": 80, "conservation": None}),
        ],
    )
    built = vm.build(res, "balanced", {"load_pct": 12, "freq_mhz": 3400}, "Ryzen", [], [], False, [], "", lang="en", amd_gpu=info)
    assert built["gpu"]["name"] == "AMD Radeon RX 7700S"
    assert built["gpu"]["temp"] == "68"
    assert built["gpu"]["clock"] == "2150"
    assert built["gpu"]["status"] == "ok"
    assert built["limit"]["available"] is True and built["limit"]["value"] == 80 and built["limit"]["statusText"] == "80 %"

    w = hardware.build_welcome(res, "AMD Ryzen 7 7735HS", {}, {}, True, lang="en", amd_gpu=info)
    assert w["gpu"] == "AMD Radeon RX 7700S"
    assert any(x["id"] == "gpu_amd" for x in w["working"])
    assert not any(x["id"] == "gpu_nvidia" for x in w["unavailable"])

    # Suspended AMD GPU
    (dgpu / "power" / "runtime_status").write_text("suspended\n")
    asleep = gpu_amd.summary(str(pci))
    assert asleep["asleep"] is True
