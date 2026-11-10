import pytest

from dockit.core import idle, processes
from dockit.core import profiles as pf


def test_idle_rule_needs_its_time_to_be_reached():
    rules = [pf.Rule("games", ["cs2"]), pf.Rule("night", [], idle=15)]
    assert pf.choose(rules, {"bash"}, True) is None
    assert pf.choose(rules, {"bash"}, True, {15}) == "night"
    assert pf.choose(rules, {"cs2"}, True, {15}) == "games"   # a running game wins: it is first
    assert pf.choose(rules, {"bash"}, True, {30}) is None


def test_idle_and_battery_must_both_hold():
    rules = [pf.Rule("night", [], when="battery", idle=10)]
    assert pf.choose(rules, set(), True, {10}) is None
    assert pf.choose(rules, set(), False, {10}) == "night"
    assert pf.choose(rules, set(), False) is None


def test_load_reads_idle_and_rejects_bad_ones(tmp_path):
    f = tmp_path / "p.toml"
    f.write_text('''
[[rules]]
profile = "night"
idle_minutes = 20
[[rules]]
profile = "work"
idle_minutes = -5
[[rules]]
profile = "games"
idle_minutes = "soon"
[[rules]]
profile = "games"
idle_minutes = true
''')
    _, rules = pf.load(f)
    assert [(r.profile, r.idle) for r in rules] == [("night", 20)]


def test_fallback(tmp_path):
    f = tmp_path / "p.toml"
    assert pf.load_fallback(tmp_path / "none.toml") == "work"
    f.write_text('fallback = "night"\n')
    assert pf.load_fallback(f) == "night"
    f.write_text('fallback = "keep"\n')
    assert pf.load_fallback(f) is None
    f.write_text('fallback = "../x"\n')
    assert pf.load_fallback(f) == "work"


def test_clean_processes():
    assert pf.clean_processes([" cs2 ", "cs2", "steam_app_*", "bad name", "a;b", "", "x" * 70]) == ["cs2", "steam_app_*"]
    assert len(pf.clean_processes([f"p{i}" for i in range(50)])) == pf.MAX_PROCESSES


def test_save_rule_keeps_other_rules_and_order(tmp_path):
    f = tmp_path / "p.toml"
    pf.save_rule("games", ["cs2", "steam"], "ac", 0, f)      # first save writes the defaults out too
    _, rules = pf.load(f)
    assert [(r.profile, r.processes, r.when) for r in rules] == [
        ("games", ["cs2", "steam"], "ac"), ("work", [], "battery")]
    pf.save_rule("night", [], "", 15, f)
    _, rules = pf.load(f)
    assert [r.profile for r in rules] == ["games", "work", "night"]
    assert rules[-1].idle == 15
    pf.save_rule("work", [], "", 0, f)                        # no condition left: the rule disappears
    _, rules = pf.load(f)
    assert [r.profile for r in rules] == ["games", "night"]


def test_save_rule_rejects_bad_values(tmp_path):
    f = tmp_path / "p.toml"
    for args in [("bad id", [], "", 0), ("games", [], "sometimes", 0), ("games", [], "", -1),
                 ("games", [], "", 5000), ("games", [], "", True)]:
        with pytest.raises(ValueError):
            pf.save_rule(*args, f)
    assert not f.exists()


def test_save_rule_keeps_profiles_and_fallback(tmp_path):
    f = tmp_path / "p.toml"
    f.write_text('fallback = "night"\n\n[profiles.movie]\nname = "Кино"\npower = "low-power"\n')
    pf.save_rule("movie", ["mpv"], "", 0, f)
    assert pf.load_fallback(f) == "night"
    assert pf.load(f)[0]["movie"].name == "Кино"
    assert pf.load(f)[1][-1].processes == ["mpv"]


def test_user_programs_filters_other_users_and_noise(tmp_path):
    def proc(pid, uid, name):
        d = tmp_path / str(pid)
        d.mkdir()
        (d / "status").write_text(f"Name:\t{name}\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n")
        (d / "comm").write_text(name + "\n")

    proc(1, 0, "cs2")
    proc(2, 1000, "cs2")
    proc(3, 1000, "bash")
    proc(4, 1000, "pipewire-pulse")
    proc(5, 1000, "Steam")
    (tmp_path / "self").mkdir()
    assert processes.user_programs(1000, str(tmp_path)) == ["cs2", "Steam"]


def test_swayidle_command_quotes_paths(tmp_path):
    cmd = idle.swayidle_command([10, 30], tmp_path / "a b")
    assert cmd[:2] == ["swayidle", "-w"]
    assert cmd.count("timeout") == 2 and "600" in cmd and "1800" in cmd
    assert any("'" in part and "a b" in part for part in cmd)   # path with a space is quoted


def test_save_fallback_and_scenario(tmp_path):
    from dockit.core import profiles as pf

    f = tmp_path / "p.toml"
    pf.save_fallback("night", f)
    assert pf.load_fallback(f) == "night"
    pf.save_fallback("keep", f)
    assert pf.load_fallback(f) is None
    with pytest.raises(ValueError):
        pf.save_fallback("bad id", f)

    s = tmp_path / "state" / "scenario"
    assert pf.load_scenario(s) == ""
    pf.save_scenario("auto", s)
    assert pf.load_scenario(s) == "auto"
    pf.save_scenario("../evil", s)           # not written
    assert pf.load_scenario(s) == "auto"


def test_profile_cards_carry_the_rule_for_editing():
    from dockit.core import profiles as pf
    from dockit.gui import viewmodel as vm

    profs = {"games": pf.Profile("games", "Игры"), "work": pf.Profile("work", "Работа")}
    rules = [pf.Rule("games", ["cs2"], "ac", 0), pf.Rule("work", [], "", 15)]
    cards = vm.profile_cards(profs, rules)
    assert cards[0]["rule"] == {"processes": ["cs2"], "when": "ac", "idle": 0, "temp": 0, "hours": ""}
    assert cards[1]["rule"] == {"processes": [], "when": "", "idle": 15, "temp": 0, "hours": ""}
    assert vm.profile_cards({"night": pf.Profile("night", "Ночь")}, [])[0]["rule"] == \
        {"processes": [], "when": "", "idle": 0, "temp": 0, "hours": ""}


def test_describe_program():
    from dockit.core.processes import describe
    assert "Steam" in describe("steam")
    assert "Шаблон" in describe("foo_*")
    assert "Steam" in describe("steam_app_730")
    assert "mygame" in describe("mygame")


def test_temperature_and_hours_rules(tmp_path):
    import datetime
    from dockit.core import profiles as pf
    f = tmp_path / "p.toml"
    pf.save_rule("night", [], "", 0, f, hours="22:00-07:00")
    pf.save_rule("work", [], "", 0, f, temp=90)
    _, rules = pf.load(f)
    assert rules[0].profile == "work" and rules[0].temp == 90          # heat protection goes first
    assert any(r.hours == "22:00-07:00" for r in rules)
    at = lambda h, m: datetime.time(h, m)
    assert pf.choose(rules, set(), None, cpu_temp=95, now=at(12, 0)) == "work"
    assert pf.choose(rules, set(), None, cpu_temp=60, now=at(23, 30)) == "night"
    assert pf.choose(rules, set(), None, cpu_temp=60, now=at(3, 0)) == "night"
    assert pf.choose(rules, set(), None, cpu_temp=None, now=at(12, 0)) != "work"


def test_hours_validation():
    from dockit.core.profiles import valid_hours, in_hours
    import datetime
    assert valid_hours("") and valid_hours("07:00-22:30")
    assert not valid_hours("7:00-22:00") and not valid_hours("25:00-01:00") and not valid_hours("abc")
    assert in_hours("09:00-17:00", datetime.time(12, 0)) and not in_hours("09:00-17:00", datetime.time(18, 0))


def test_brightness_refresh_create_delete(tmp_path):
    from dockit.core import profiles as pf
    f = tmp_path / "p.toml"
    pf.save_profile("work", "balanced", "keep", "", "", f, brightness=60, refresh=60)
    profs, _ = pf.load(f)
    assert profs["work"].brightness == 60 and profs["work"].refresh == 60
    pf.save_profile("work", "balanced", "keep", "", "", f)
    profs, _ = pf.load(f)
    assert profs["work"].brightness is None and profs["work"].refresh is None
    pid = pf.create_profile("Кино", f)
    assert pid == "custom1"
    pf.save_rule(pid, ["mpv"], "", 0, f)
    pf.save_fallback(pid, f)
    pf.delete_profile(pid, f)
    profs, rules = pf.load(f)
    assert pid not in profs and all(r.profile != pid for r in rules)
    assert pf.load_fallback(f) is None
    import pytest
    with pytest.raises(ValueError):
        pf.delete_profile("games", f)
    with pytest.raises(ValueError):
        pf.save_profile("work", "balanced", "keep", "", "", f, brightness=200)


def test_display_helpers(tmp_path):
    from dockit.core import display
    d = tmp_path / "bl"
    (d / "amdgpu_bl1").mkdir(parents=True)
    (d / "amdgpu_bl1" / "max_brightness").write_text("255")
    (d / "amdgpu_bl1" / "brightness").write_text("128")
    assert display.brightness_percent(str(d)) == 50
    out = {"eDP-1": {"modes": [{"width": 2560, "height": 1600, "refresh_rate": 165000},
                               {"width": 2560, "height": 1600, "refresh_rate": 60001},
                               {"width": 1920, "height": 1200, "refresh_rate": 120000}], "current_mode": 0}}
    info = display.refresh_info(out)
    assert info == {"output": "eDP-1", "current": 165, "rates": [60, 165]}
    from dockit.daemon import actions
    actions.set_brightness(20, str(d))
    assert (d / "amdgpu_bl1" / "brightness").read_text() == "51"
    import pytest
    with pytest.raises(actions.ActionError):
        actions.set_brightness(0, str(d))


def test_tuning_and_battery_estimate(tmp_path):
    from dockit.core import tuning
    from dockit.daemon import actions
    from dockit.modules.battery import minutes_left, read_batteries
    base = tmp_path / "cpu"
    (base / "cpufreq").mkdir(parents=True)
    (base / "cpufreq" / "boost").write_text("1")
    (base / "cpu0" / "cpufreq").mkdir(parents=True)
    (base / "cpu0" / "cpufreq" / "energy_performance_available_preferences").write_text("performance balance_power power")
    (base / "cpu0" / "cpufreq" / "energy_performance_preference").write_text("balance_power")
    assert tuning.read_boost(str(base)) is True
    actions.set_boost(False, str(base))
    assert (base / "cpufreq" / "boost").read_text() == "0"
    actions.set_epp("power", str(base))
    assert tuning.read_epp(str(base)) == "power"
    import pytest
    with pytest.raises(actions.ActionError):
        actions.set_epp("turbo-everything", str(base))
    ps = tmp_path / "ps" / "BAT0"
    ps.mkdir(parents=True)
    for name, val in {"capacity": 50, "status": "Discharging", "energy_now": 40_000_000,
                      "energy_full": 80_000_000, "energy_full_design": 90_000_000, "power_now": 20_000_000}.items():
        (ps / name).write_text(str(val))
    b = read_batteries(str(tmp_path / "ps"))[0]
    assert b["power_w"] == 20.0 and b["energy_wh"] == 40.0
    assert minutes_left(b) == 120


def test_bluetooth_info_parse():
    from dockit.core.bluetooth import parse_info
    text = "Device AA:BB:CC:DD:EE:FF (public)\n\tName: EPOS H3PRO\n\tIcon: audio-headset\n\tBattery Percentage: 0x55 (85)\n"
    assert parse_info(text) == {"name": "EPOS H3PRO", "battery": 85, "icon": "audio-headset"}
    assert parse_info("Name: Mouse\n")["battery"] is None


def test_hyprland_refresh():
    from dockit.core import display
    mon = {"name": "eDP-1", "width": 2560, "height": 1600, "refreshRate": 165.0, "x": 0, "y": 0, "scale": 1.0,
           "availableModes": ["2560x1600@165.00Hz", "2560x1600@60.00Hz", "1920x1200@120.00Hz"]}
    assert display.refresh_info({}, [mon]) == {"output": "eDP-1", "current": 165, "rates": [60, 165]}


def test_display_parsers_for_sway_kde_x11():
    import json
    from dockit.core import display
    sway = json.dumps([{"name": "eDP-1", "active": True,
                        "current_mode": {"width": 2560, "height": 1600, "refresh": 165000},
                        "modes": [{"width": 2560, "height": 1600, "refresh": 165000},
                                  {"width": 2560, "height": 1600, "refresh": 60000}]}])
    assert display.parse_sway(sway)["rates"] == [60, 165]
    kde = json.dumps({"outputs": [{"name": "eDP-1", "enabled": True, "currentModeId": "1",
                                   "modes": [{"id": "1", "size": {"width": 2560, "height": 1600}, "refreshRate": 165.0},
                                             {"id": "2", "size": {"width": 2560, "height": 1600}, "refreshRate": 60.0},
                                             {"id": "3", "size": {"width": 1920, "height": 1200}, "refreshRate": 120.0}]}]})
    parsed = display.parse_kscreen(kde)
    assert parsed["rates"] == [60, 165] and parsed["modes"][60] == "2" and parsed["current"] == 165
    x = ("Screen 0: minimum 16 x 16\neDP-1 connected primary 2560x1600+0+0 (normal) 340mm x 210mm\n"
         "   2560x1600    165.00*+  60.00 \n   1920x1200    120.00 \nHDMI-1 disconnected (normal)\n")
    px = display.parse_xrandr(x)
    assert px["output"] == "eDP-1" and px["current"] == 165 and px["rates"] == [60, 165] and px["size"] == "2560x1600"
