import pytest

from dockit.core import hardware, session_state, tuning
from dockit.core.scanner import ScanItem, ScanResult
from dockit.core.status import Status
from dockit.daemon import actions
from dockit.gui import viewmodel as vm


def _make_cpu_sysfs(tmp_path, driver: str, epp_avail: str, epp_cur: str = "balance_performance", gov: str = "powersave"):
    cpu0 = tmp_path / "cpu0" / "cpufreq"
    cpu1 = tmp_path / "cpu1" / "cpufreq"
    cpu0.mkdir(parents=True)
    cpu1.mkdir(parents=True)
    (cpu0 / "scaling_driver").write_text(driver + "\n")
    (cpu0 / "scaling_available_governors").write_text("performance powersave\n")
    (cpu0 / "scaling_governor").write_text(gov + "\n")
    (cpu1 / "scaling_governor").write_text(gov + "\n")
    (cpu0 / "energy_performance_available_preferences").write_text(epp_avail + "\n")
    (cpu0 / "energy_performance_preference").write_text(epp_cur + "\n")
    (cpu1 / "energy_performance_preference").write_text(epp_cur + "\n")
    return str(tmp_path)


def test_epp_choices_hides_custom_marker_and_detects_dynamic(tmp_path):
    amd = _make_cpu_sysfs(
        tmp_path / "amd",
        "amd-pstate-epp",
        "default performance balance_performance balance_power power custom dynamic",
    )
    choices = tuning.epp_choices(amd)
    assert "custom" not in choices
    assert "dynamic" in choices
    assert tuning.has_dynamic_epp(amd) is True
    assert tuning.cpu_driver(amd) == "amd-pstate-epp"

    intel = _make_cpu_sysfs(
        tmp_path / "intel",
        "intel_pstate",
        "default performance balance_performance balance_power power",
    )
    assert tuning.epp_choices(intel) == ["default", "performance", "balance_performance", "balance_power", "power"]
    assert tuning.has_dynamic_epp(intel) is False
    assert tuning.cpu_driver(intel) == "intel_pstate"


def test_set_power_profile_dynamic_on_amd_and_refused_on_intel(tmp_path):
    prof = tmp_path / "platform_profile"
    choices = tmp_path / "platform_profile_choices"
    prof.write_text("performance\n")
    choices.write_text("low-power balanced performance\n")

    amd = _make_cpu_sysfs(
        tmp_path / "amd",
        "amd-pstate-epp",
        "default performance balance_performance balance_power power custom dynamic",
        epp_cur="performance",
        gov="performance",
    )
    res = actions.set_power_profile("dynamic", str(prof), str(choices), cpu_base=amd)
    assert res == {"profile": "balanced", "epp": "dynamic"}
    assert prof.read_text().strip() == "balanced"
    assert tuning.read_epp(amd) == "dynamic"

    # Leaving dynamic without power-profiles-daemon restores a manual EPP,
    # including when Linux 7.x reports "dynamic(profile:performance)".
    (tmp_path / "amd" / "cpu0" / "cpufreq" / "energy_performance_preference").write_text("dynamic(profile:performance)\n")
    (tmp_path / "amd" / "cpu1" / "cpufreq" / "energy_performance_preference").write_text("dynamic(profile:performance)\n")
    assert tuning.is_dynamic_epp(tuning.read_epp(amd)) is True
    assert tuning.is_dynamic_epp("balance_performance") is False
    actions._sync_power_state("balanced", cpu_base=amd, use_ppd=False)
    assert tuning.read_epp(amd) == "balance_performance"

    # On Intel (no dynamic in sysfs), "dynamic" is cleanly rejected.
    intel = _make_cpu_sysfs(
        tmp_path / "intel",
        "intel_pstate",
        "default performance balance_performance balance_power power",
    )
    with pytest.raises(actions.ActionError):
        actions.set_power_profile("dynamic", str(prof), str(choices), cpu_base=intel)


def test_modes_for_lang_includes_dynamic_only_when_supported():
    assert [m["id"] for m in vm.modes_for_lang("ru", has_dynamic=False)] == ["low-power", "balanced", "performance"]
    assert [m["id"] for m in vm.modes_for_lang("ru", has_dynamic=True)] == [
        "low-power", "balanced", "dynamic", "performance"
    ]
    assert vm.modes_for_lang("en", has_dynamic=True)[2]["name"] == "Dynamic"
    assert vm.modes_for_lang("uk", has_dynamic=True)[2]["name"] == "Динамічний"


def test_session_state_saves_and_restores_dynamic_mode(tmp_path):
    p = tmp_path / "session.json"
    session_state.save({"power": "dynamic"}, path=p)
    assert session_state.load(path=p) == {"power": "dynamic"}

    sent = []
    applied = session_state.restore(
        lambda req: sent.append(req) or {"profile": "balanced", "epp": "dynamic"},
        path=p,
        current_power_fn=lambda: "balanced",
        discover_kbd_fn=lambda: [],
    )
    assert applied == ["power=dynamic"]
    assert sent == [{"action": "set_power_profile", "value": "dynamic", "interactive": False}]


def test_welcome_report_for_amd_laptop_intel_laptop_and_desktop_pc(tmp_path):
    # 1. AMD laptop on Hyprland
    dmi_lap = tmp_path / "dmi_lap"
    dmi_lap.mkdir()
    (dmi_lap / "chassis_type").write_text("10\n")  # Notebook

    amd_scan = ScanResult(
        system={"vendor": "GIGABYTE", "model": "GIGABYTE GAMING A16 3VH", "kernel": "7.3.5"},
        items=[
            ScanItem("service", "Service", "systemd", Status.OK, "ok"),
            ScanItem("battery", "Battery", "ps", Status.OK, "90%"),
            ScanItem("sensors", "Sensors", "hwmon", Status.OK, "ok", state={"temps_c": {"k10temp/t1": 45}, "fans_rpm": {}}),
            ScanItem("gpu_nvidia", "NVIDIA", "smi", Status.OK, "ok", state={"name": "NVIDIA RTX 5060"}),
        ],
    )
    w_amd = hardware.build_welcome(
        amd_scan,
        "AMD Ryzen 7 260 w/ Radeon 780M Graphics",
        {"driver": "amd-pstate-epp", "hasDynamic": True, "boost": True, "eppChoices": ["performance", "power"]},
        {"rates": [60, 165]},
        idle_available=True,
        lang="ru",
        dmi_dir=str(dmi_lap),
        env={"HYPRLAND_INSTANCE_SIGNATURE": "abc"},
    )
    assert w_amd["formFactor"] == "laptop"
    assert w_amd["cpuVendor"] == "amd"
    assert w_amd["desktop"] == "Hyprland"
    assert any(x["id"] == "dynamic_cpu" for x in w_amd["working"])
    assert any(x["id"] == "fans" for x in w_amd["unavailable"])

    # 2. Intel laptop on KDE Plasma (no dynamic EPP)
    intel_scan = ScanResult(
        system={"vendor": "LENOVO", "model": "ThinkPad X1 Carbon", "kernel": "6.12.0"},
        items=[
            ScanItem("service", "Service", "systemd", Status.NEEDS_SETUP, "stopped", hint="install"),
            ScanItem("battery", "Battery", "ps", Status.OK, "80%"),
            ScanItem("sensors", "Sensors", "hwmon", Status.OK, "ok", state={"temps_c": {"coretemp/t1": 42}, "fans_rpm": {"thinkpad/fan1": 2100}}),
        ],
    )
    w_intel = hardware.build_welcome(
        intel_scan,
        "13th Gen Intel(R) Core(TM) i7-1365U",
        {"driver": "intel_pstate", "hasDynamic": False, "boost": None, "eppChoices": ["performance", "balance_power", "power"]},
        {"rates": [60]},
        idle_available=False,
        lang="en",
        dmi_dir=str(dmi_lap),
        env={"XDG_CURRENT_DESKTOP": "KDE"},
    )
    assert w_intel["formFactor"] == "laptop"
    assert w_intel["cpuVendor"] == "intel"
    assert w_intel["desktop"] == "KDE Plasma"
    assert any(x["id"] == "cpu_tuning" for x in w_intel["working"])
    dyn_unavail = next(x for x in w_intel["unavailable"] if x["id"] == "dynamic_cpu")
    assert "Intel" in dyn_unavail["detail"]
    assert any(x["id"] == "swayidle" for x in w_intel["needsSetup"])
    assert not any(x["id"] == "fans" for x in w_intel["unavailable"])  # ThinkPad exposes fans!

    # 3. Desktop PC (chassis_type = 3, no battery)
    dmi_pc = tmp_path / "dmi_pc"
    dmi_pc.mkdir()
    (dmi_pc / "chassis_type").write_text("3\n")  # Desktop

    pc_scan = ScanResult(
        system={"vendor": "ASUS", "model": "B650-PLUS", "kernel": "6.14.0"},
        items=[
            ScanItem("battery", "Battery", "ps", Status.UNAVAILABLE, "no battery"),
            ScanItem("battery_limit", "Limit", "ps", Status.UNAVAILABLE, "no limit"),
        ],
    )
    w_pc = hardware.build_welcome(
        pc_scan,
        "AMD Ryzen 7 7800X3D",
        {"driver": "amd-pstate-epp", "hasDynamic": False, "boost": True, "eppChoices": ["performance", "power"]},
        {"rates": []},
        idle_available=True,
        lang="en",
        dmi_dir=str(dmi_pc),
        env={"DISPLAY": ":0"},
    )
    assert w_pc["formFactor"] == "desktop"
    assert w_pc["formLabel"] == "Desktop PC"
    assert any(x["id"] == "battery" and "desktop" in x["detail"].lower() for x in w_pc["unavailable"])
    assert not any(x["id"] == "battery_limit" for x in w_pc["unavailable"])
