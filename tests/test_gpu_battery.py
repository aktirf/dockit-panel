from dockit.modules.battery import ac_online, read_batteries
from dockit.modules.gpu_nvidia import parse_smi_csv


def test_parse_smi_normal_line():
    gpus = parse_smi_csv("NVIDIA GeForce RTX 5060 Max-Q, 42, 7.12, 50.00, 15, 8151, 17, 210\n")
    assert gpus == [
        {
            "name": "NVIDIA GeForce RTX 5060 Max-Q",
            "temp_c": 42,
            "power_w": 7.12,
            "power_limit_w": 50,
            "mem_used_mb": 15,
            "mem_total_mb": 8151,
            "util_pct": 17,
            "clock_mhz": 210,
        }
    ]


def test_parse_smi_not_available_values_and_comma_in_name():
    gpus = parse_smi_csv("Weird, Name Card, 40, [N/A], [N/A], 15, 8000, 100, 300")
    assert gpus[0]["name"] == "Weird, Name Card"
    assert gpus[0]["power_w"] is None
    assert gpus[0]["mem_total_mb"] == 8000


def test_parse_smi_ignores_garbage():
    assert parse_smi_csv("") == []
    assert parse_smi_csv("NVIDIA-SMI has failed") == []


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n")


def test_read_battery_health_and_ac(tmp_path):
    bat = tmp_path / "BAT1"
    _write(bat / "capacity", "66")
    _write(bat / "status", "Discharging")
    _write(bat / "energy_full", "70000000")
    _write(bat / "energy_full_design", "80000000")
    _write(tmp_path / "ACAD" / "type", "Mains")
    _write(tmp_path / "ACAD" / "online", "1")
    (b,) = read_batteries(str(tmp_path))
    assert b["percent"] == 66 and b["status"] == "Discharging"
    assert b["health_pct"] == 87.5
    assert ac_online(str(tmp_path)) is True


def test_no_battery(tmp_path):
    assert read_batteries(str(tmp_path)) == []
    assert ac_online(str(tmp_path)) is None
