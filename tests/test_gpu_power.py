import os

from dockit.core import gpu_power
from dockit.core.status import Status
from dockit.gui.viewmodel import gpu_sleep_view
from dockit.modules import gpu_nvidia
from dockit.modules.gpu_nvidia import GpuNvidia


def _pci(tmp_path, runtime="suspended", control="auto"):
    base = tmp_path / "pci"
    card = base / "0000:01:00.0"
    (card / "power").mkdir(parents=True)
    (card / "vendor").write_text("0x10de\n")
    (card / "class").write_text("0x030200\n")
    (card / "power" / "runtime_status").write_text(runtime + "\n")
    (card / "power" / "control").write_text(control + "\n")
    audio = base / "0000:01:00.1"  # the card's HDMI sound part: NVIDIA, but not a display device
    audio.mkdir()
    (audio / "vendor").write_text("0x10de\n")
    (audio / "class").write_text("0x040300\n")
    amd = base / "0000:65:00.0"
    amd.mkdir()
    (amd / "vendor").write_text("0x1002\n")
    (amd / "class").write_text("0x030000\n")
    return str(base)


def _proc(tmp_path, programs):
    """programs: {pid: (name, [device files])}; fds are symlinks like in /proc."""
    base = tmp_path / "proc"
    for pid, (name, targets) in programs.items():
        fd = base / str(pid) / "fd"
        fd.mkdir(parents=True)
        (base / str(pid) / "comm").write_text(name + "\n")
        for n, target in enumerate(targets):
            os.symlink(target, fd / str(n))
    (base / "self").mkdir(parents=True)  # non-numeric entries are ignored
    return str(base)


def test_finds_only_nvidia_display_devices(tmp_path):
    gpus = gpu_power.nvidia_gpus(_pci(tmp_path))
    assert [os.path.basename(g) for g in gpus] == ["0000:01:00.0"]


def test_asleep(tmp_path):
    assert gpu_power.gpu_asleep(_pci(tmp_path / "a", "suspended")) is True
    assert gpu_power.gpu_asleep(_pci(tmp_path / "b", "active")) is False
    assert gpu_power.gpu_asleep(str(tmp_path / "empty")) is False  # no card: not "asleep"


def test_nvidia_device_names():
    for good in ("/dev/nvidia0", "/dev/nvidia1", "/dev/nvidiactl", "/dev/nvidia-modeset",
                 "/dev/nvidia-uvm", "/dev/nvidia-uvm-tools"):
        assert gpu_power.is_nvidia_node(good), good
    for bad in ("/dev/null", "/dev/dri/card1", "/dev/nvidia0x", "/home/u/nvidia0", "socket:[123]"):
        assert not gpu_power.is_nvidia_node(bad), bad


def test_gpu_users(tmp_path):
    proc = _proc(tmp_path, {
        10: ("steam", ["/dev/null", "/dev/nvidiactl", "/dev/nvidia0"]),
        11: ("firefox", ["/dev/nvidiactl"]),
        12: ("bash", ["/dev/pts/1"]),
        13: ("Blender", ["/dev/nvidia0", "/dev/nvidia0"]),
    })
    users = gpu_power.gpu_users(proc)
    assert users == [
        {"pid": 13, "name": "Blender", "card": True},
        {"pid": 10, "name": "steam", "card": True},
        {"pid": 11, "name": "firefox", "card": False},
    ]


def test_summary(tmp_path):
    info = gpu_power.summary(_pci(tmp_path, "active", "auto"), _proc(tmp_path, {5: ("game", ["/dev/nvidia0"])}))
    assert info["asleep"] is False and info["runtime"] == "active" and info["control"] == "auto"
    assert info["users"][0]["name"] == "game"
    assert gpu_power.summary(str(tmp_path / "nothing")) is None


def test_sleeping_card_is_not_woken_by_nvidia_smi(tmp_path, monkeypatch):
    def must_not_run():
        raise AssertionError("nvidia-smi was called while the card sleeps")

    monkeypatch.setattr(gpu_nvidia, "_query", must_not_run)
    monkeypatch.setattr(GpuNvidia, "last_name", "NVIDIA GeForce RTX 5060")
    mod = GpuNvidia(_pci(tmp_path, "suspended"), _proc(tmp_path, {}))
    assert mod.detect().status is Status.OK
    state = mod.get_state()
    assert state["asleep"] is True and state["name"] == "NVIDIA GeForce RTX 5060"


def test_awake_card_asks_nvidia_smi_once_per_scan(tmp_path, monkeypatch):
    calls = []

    def query():
        calls.append(1)
        return [{"name": "RTX", "temp_c": 50}], ""

    monkeypatch.setattr(gpu_nvidia, "_query", query)
    mod = GpuNvidia(_pci(tmp_path, "active"), _proc(tmp_path, {}))
    assert mod.detect().status is Status.OK
    state = mod.get_state()
    assert len(calls) == 1
    assert state["asleep"] is False and state["temp_c"] == 50 and state["sleep"]["runtime"] == "active"


def test_sleep_view_texts():
    assert gpu_sleep_view(None)["sleepTip"] == ""
    asleep = gpu_sleep_view({"sleep": {"asleep": True, "runtime": "suspended", "control": "auto", "users": []}})
    assert asleep["asleep"] is True and asleep["sleepText"] == "спит"

    held = gpu_sleep_view({"sleep": {"asleep": False, "runtime": "active", "control": "auto", "users": [
        {"pid": 1, "name": "steam", "card": True}, {"pid": 2, "name": "steam", "card": True},
        {"pid": 3, "name": "firefox", "card": False}]}})
    assert held["holders"] == ["steam"] and "steam" in held["sleepTip"] and "firefox" not in held["sleepTip"]

    never = gpu_sleep_view({"sleep": {"asleep": False, "runtime": "active", "control": "on", "users": []}})
    assert never["sleepText"] == "не засыпает" and "power/control" in never["sleepTip"]

    free = gpu_sleep_view({"sleep": {"asleep": False, "runtime": "active", "control": "auto", "users": []}})
    assert free["sleepText"] == "работает" and free["holders"] == []
