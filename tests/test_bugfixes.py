import json

from dockit.core import bluetooth, idle, profiles as pf
from dockit.core.status import Status
from dockit.gui import app as gui_app
from dockit.gui import viewmodel as vm
from dockit.modules import audio as audio_mod
from dockit.modules import sensors, wireless


def test_bluetooth_parse_powered():
    sample_on = "Controller AA:BB:CC:DD:EE:FF (public)\n\tName: host\n\tPowered: yes\n\tDiscoverable: no\n"
    sample_off = "Controller AA:BB:CC:DD:EE:FF (public)\n\tPowered: no\n"
    assert bluetooth.parse_powered(sample_on) is True
    assert bluetooth.parse_powered(sample_off) is False
    assert bluetooth.parse_powered("No default controller available") is None


def test_wireless_combines_rfkill_and_bluez_power(tmp_path):
    """Regression test: `bluetoothctl power off` leaves rfkill soft=0, so wireless
    must report bluetooth=False when BlueZ says Powered: no."""
    rf = tmp_path / "rfkill"
    (rf / "rfkill0").mkdir(parents=True)
    (rf / "rfkill0" / "type").write_text("wlan\n")
    (rf / "rfkill0" / "soft").write_text("0\n")
    (rf / "rfkill0" / "hard").write_text("0\n")
    (rf / "rfkill1").mkdir(parents=True)
    (rf / "rfkill1" / "type").write_text("bluetooth\n")
    (rf / "rfkill1" / "soft").write_text("0\n")
    (rf / "rfkill1" / "hard").write_text("0\n")

    assert wireless._read_all(str(rf), bt_powered=lambda: False) == {"wlan": True, "bluetooth": False}
    assert wireless._read_all(str(rf), bt_powered=lambda: True) == {"wlan": True, "bluetooth": True}
    # Without bluetoothctl, fall back to rfkill.
    assert wireless._read_all(str(rf), bt_powered=lambda: None) == {"wlan": True, "bluetooth": True}

    # If rfkill itself soft-blocks Bluetooth, do not even ask bluetoothctl.
    (rf / "rfkill1" / "soft").write_text("1\n")
    called = []
    assert wireless._read_all(str(rf), bt_powered=lambda: called.append(1) or True) == {
        "wlan": True,
        "bluetooth": False,
    }
    assert called == []


def test_wireless_module_caches_single_scan(tmp_path):
    rf = tmp_path / "rfkill"
    (rf / "rfkill0").mkdir(parents=True)
    (rf / "rfkill0" / "type").write_text("bluetooth\n")
    (rf / "rfkill0" / "soft").write_text("0\n")
    calls = []
    mod = wireless.Wireless(str(rf), bt_powered=lambda: calls.append(1) or False)
    assert mod.detect().status is Status.OK
    assert mod.get_state() == {"bluetooth": False}
    assert len(calls) == 1


def test_sensors_keeps_duplicate_chip_names(tmp_path):
    hw = tmp_path / "hwmon"
    for idx, temp_mc in ((0, "78000"), (1, "40000")):
        d = hw / f"hwmon{idx}"
        d.mkdir(parents=True)
        (d / "name").write_text("nvme\n")
        (d / "temp1_input").write_text(temp_mc + "\n")
    data = sensors._read_all(str(hw))
    assert len(data["temps_c"]) == 2
    assert set(data["temps_c"].values()) == {78.0, 40.0}
    # viewmodel.chip_temps must report the hotter SSD, not be overwritten by the cooler one.
    assert vm.chip_temps(data)["SSD (NVMe)"] == 78.0


def test_idle_watcher_reaps_process_on_stop(tmp_path):
    events = []

    class FakeProc:
        def poll(self):
            return None

        def terminate(self):
            events.append("terminate")

        def wait(self, timeout=None):
            events.append("wait")
            return 0

    watcher = idle.IdleWatcher()
    watcher.directory = tmp_path / "flags"
    watcher.directory.mkdir()
    (watcher.directory / "5").write_text("")
    watcher._proc = FakeProc()
    watcher._minutes = [5]

    watcher.stop()
    assert events == ["terminate", "wait"]
    assert watcher._proc is None
    assert not (watcher.directory / "5").exists()


def test_profile_apply_collects_non_daemon_errors(monkeypatch):
    from dockit.core import audio, display

    monkeypatch.setattr(display, "set_refresh", lambda hz: "Частота экрана: не удалось")
    monkeypatch.setattr(audio, "set_default", lambda kind, q: (_ for _ in ()).throw(audio.AudioError("нет наушников")))
    errors = []
    pf.apply(pf.Profile("g", "Игры", refresh=165, output="epos"), lambda r: {}, errors=errors)
    assert any("Частота экрана" in e for e in errors)
    assert any("нет наушников" in e for e in errors)


def test_audio_module_state_is_json_serializable(monkeypatch):
    from dockit.core import audio

    monkeypatch.setattr(
        audio,
        "list_devices",
        lambda: [audio.AudioDevice("output", "s0", "Speakers", 50, False, True)],
    )
    mod = audio_mod.Audio()
    assert mod.detect().status is Status.OK
    state = mod.get_state()
    dumped = json.dumps(state)
    assert "Speakers" in dumped


def test_single_instance_socket_name():
    name = gui_app.instance_socket_name()
    assert name.startswith("dockit-gui-")


def test_save_profile_refuses_to_wipe_broken_toml(tmp_path):
    broken = "[profiles.mygame\npower = 'performance'\n"
    f = tmp_path / "profiles.toml"
    f.write_text(broken, encoding="utf-8")

    import pytest

    with pytest.raises(ValueError):
        pf.save_profile("games", "balanced", "keep", "", "", f)
    with pytest.raises(ValueError):
        pf.save_rule("games", ["cs2"], "", 0, f)
    with pytest.raises(ValueError):
        pf.save_fallback("work", f)
    with pytest.raises(ValueError):
        pf.create_profile("Movie", f)
    with pytest.raises(ValueError):
        pf.delete_profile("custom1", f)

    assert f.read_text(encoding="utf-8") == broken


def test_profiles_allow_refresh_up_to_500hz(tmp_path):
    import pytest

    f = tmp_path / "profiles.toml"
    pf.save_profile("games", "performance", "keep", "", "", f, refresh=480)
    assert pf.load(f)[0]["games"].refresh == 480
    pf.save_profile("games", "performance", "keep", "", "", f, refresh=500)
    assert pf.load(f)[0]["games"].refresh == 500
    with pytest.raises(ValueError):
        pf.save_profile("games", "performance", "keep", "", "", f, refresh=501)


def test_hyprland_rotated_monitor_rates_and_transform():
    from dockit.core import display

    rotated = {
        "name": "eDP-2",
        "width": 1600,
        "height": 2560,
        "x": 0,
        "y": 0,
        "scale": 1.0,
        "transform": 1,
        "refreshRate": 165.0,
        "availableModes": ["2560x1600@165.00Hz", "2560x1600@60.00Hz"],
    }
    info = display.refresh_info({}, [rotated])
    assert info == {"output": "eDP-2", "current": 165, "rates": [60, 165]}
    cmd = display.hypr_lua_command(rotated, 60)
    assert 'mode="2560x1600@60.00"' in cmd
    assert "transform=1" in cmd


def test_gpu_power_summary_skips_proc_scan_when_asleep(tmp_path, monkeypatch):
    from dockit.core import gpu_power

    base = tmp_path / "pci"
    card = base / "0000:01:00.0"
    (card / "power").mkdir(parents=True)
    (card / "vendor").write_text("0x10de\n")
    (card / "class").write_text("0x030200\n")
    (card / "power" / "runtime_status").write_text("suspended\n")
    (card / "power" / "control").write_text("auto\n")

    def must_not_scan(_proc):
        raise AssertionError("gpu_users should not scan /proc when GPU is asleep")

    monkeypatch.setattr(gpu_power, "gpu_users", must_not_scan)
    info = gpu_power.summary(str(base))
    assert info["asleep"] is True
    assert info["users"] == []


def test_localization_of_explain_describe_display_and_client(tmp_path):
    from dockit.core import display, processes
    from dockit.daemon import client

    rule = pf.Rule("games", ["cs2"], when="ac", idle=10, temp=90, hours="22:00-07:00")
    en_reason = pf.explain(rule, {"cs2"}, lang="en")
    assert "90 °C" in en_reason and "on AC power" in en_reason and "idle for 10 min" in en_reason
    assert not any("а" <= ch.lower() <= "я" for ch in en_reason)

    uk_reason = pf.explain(rule, {"cs2"}, lang="uk")
    assert "підключено зарядку" in uk_reason

    assert "browser" in processes.describe("firefox", lang="en").lower()
    assert "Pattern" in processes.describe("foo_*", lang="en")
    assert "Steam" in processes.describe("steam_app_730", lang="en")
    assert "браузер" in processes.describe("firefox", lang="uk").lower()

    err_en = display.set_refresh(60, outputs={}, monitors=[], lang="en")
    assert err_en and "not supported" in err_en.lower()

    res, err = client.ask({"action": "ping"}, path=str(tmp_path / "missing.sock"), lang="en")
    assert res is None and "not running" in err.lower()
    assert "not authorized" in client.localize_daemon_error("Действие не подтверждено.", "en").lower()
    assert "не підтверджено" in client.localize_daemon_error("Действие не подтверждено.", "uk").lower()


def test_no_dead_backlight_page():
    from pathlib import Path

    qml_dir = Path(__file__).resolve().parents[1] / "src/dockit/gui/qml"
    assert not (qml_dir / "BacklightPage.qml").exists()
    assert "BacklightPage" not in (qml_dir / "Main.qml").read_text(encoding="utf-8")
    assert "BacklightPage" not in (qml_dir / "qmldir").read_text(encoding="utf-8")


def test_every_qml_flow_has_stable_width_constraint():
    """Regression test: Flow without Layout.fillWidth or anchors inside a GridLayout jumps on relayout."""
    from pathlib import Path

    qml_dir = Path(__file__).resolve().parents[1] / "src/dockit/gui/qml"
    for path in sorted(qml_dir.glob("*.qml")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines):
            if line.strip() == "Flow {":
                block = "\n".join(lines[idx : idx + 8])
                assert ("Layout.fillWidth: true" in block) or ("anchors.right:" in block), (
                    f"{path.name}:{idx + 1} Flow lacks stable width constraint"
                )
