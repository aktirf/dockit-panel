from dockit.core.cpu import CpuMonitor
from dockit.core.scanner import ScanItem, ScanResult
from dockit.core.status import Status
from dockit.gui import viewmodel as vm


def _result():
    return ScanResult(
        system={"vendor": "GIGABYTE", "model": "GIGABYTE GAMING A16 3VH"},
        items=[
            ScanItem("service", "Служба", "x", Status.OK, "ok"),
            ScanItem("sensors", "Температуры", "hwmon", Status.OK, "ok",
                     state={"temps_c": {"k10temp/temp1_input": 41.0, "nvme/temp1_input": 60.0}, "fans_rpm": {}}),
            ScanItem("gpu_nvidia", "Видеокарта", "smi", Status.OK, "ok",
                     state={"name": "RTX", "clock_mhz": 1552, "util_pct": 0, "temp_c": 45,
                            "mem_used_mb": 800, "mem_total_mb": 8000, "power_w": 12.4}),
            ScanItem("battery", "Батарея", "ps", Status.OK, "ok",
                     state={"batteries": [{"percent": 100, "status": "Full", "health_pct": 100.0, "cycles": 6}],
                            "ac_online": True}),
            ScanItem("battery_limit", "Лимит", "x", Status.UNAVAILABLE, "no", hint="Обновите ядро"),
            ScanItem("camera", "Камера", "x", Status.OK, "ok", state={"enabled": True}),
            ScanItem("wireless", "Wi-Fi", "x", Status.OK, "ok", state={"wlan": True, "bluetooth": False}),
        ],
    )


def _build(**kw):
    args = dict(current_mode="balanced", cpu={"load_pct": 5, "freq_mhz": 3800}, cpu_name="Ryzen",
                cpu_history=[40, 41], gpu_history=[45], mic_muted=False,
                scenarios=[{"id": "games", "name": "Игры"}], scenario="")
    args.update(kw)
    return vm.build(_result(), **args)


def test_number_format_uses_comma():
    assert vm.num(3.8, 1) == "3,8"
    assert vm.num(None) == "—"
    assert vm.num(41.0) == "41"


def test_model_name_without_vendor():
    assert vm.short_model({"vendor": "GIGABYTE", "model": "GIGABYTE GAMING A16 3VH"}) == "GAMING A16 3VH"


def test_cpu_temperature_ignores_other_chips():
    assert vm.cpu_temperature({"temps_c": {"k10temp/temp1_input": 41.0, "nvme/temp1_input": 60.0}}) == 41.0
    assert vm.cpu_temperature({"temps_c": {"nvme/temp1_input": 60.0}}) is None
    assert vm.cpu_temperature(None) is None


def test_overview_data():
    d = _build()
    assert d["ready"] and d["model"] == "GAMING A16 3VH"
    assert d["service"] is True and d["okCount"] == 6 and d["total"] == 7
    assert d["cpu"]["freq"] == "3,8" and d["cpu"]["temp"] == "41" and d["cpu"]["fan"] == "нет данных"
    assert d["gpu"]["memUsed"] == "0,8" and d["gpu"]["memPct"] == 10
    assert d["battery"]["text"] == "Полностью заряжена" and d["battery"]["source"] == "От сети"
    assert d["limit"]["status"] == "no"


def test_toggles_camera_needs_service_and_wireless_is_view_only():
    toggles = {t["id"]: t for t in _build()["toggles"]}
    assert toggles["camera"]["can"] and toggles["camera"]["on"]
    assert toggles["mic"]["can"] and toggles["mic"]["on"]
    assert not toggles["wifi"]["can"] and toggles["wifi"]["on"]
    assert not toggles["bluetooth"]["on"]
    assert not {t["id"]: t for t in _build(mic_muted=None)["toggles"]}["mic"]["can"]


def test_problem_features_come_first_and_counts_exist():
    d = _build()
    assert d["features"][0]["status"] == "no"
    assert {"status": "no", "text": "Недоступно: 1"} in d["counts"]


def test_empty_state_has_every_key_the_window_reads():
    e = vm.empty()
    for key in _build():
        assert key in e


def test_cpu_monitor_load(tmp_path):
    stat = tmp_path / "stat"
    stat.write_text("cpu  100 0 100 800 0 0 0 0\n")
    cpu_dir = tmp_path / "cpu"
    (cpu_dir / "cpu0" / "cpufreq").mkdir(parents=True)
    (cpu_dir / "cpu0" / "cpufreq" / "scaling_cur_freq").write_text("3800000\n")
    m = CpuMonitor(str(stat), str(cpu_dir), str(tmp_path / "none"))
    stat.write_text("cpu  150 0 150 900 0 0 0 0\n")  # +100 busy, +100 idle
    sample = m.sample()
    assert sample["load_pct"] == 50 and sample["freq_mhz"] == 3800


def test_cpu_monitor_without_files(tmp_path):
    m = CpuMonitor(str(tmp_path / "a"), str(tmp_path / "b"), str(tmp_path / "c"))
    assert m.sample() == {"load_pct": None, "freq_mhz": None}
