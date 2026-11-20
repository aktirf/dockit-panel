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
