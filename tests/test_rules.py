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
