from dockit.core import profiles as pf


def test_defaults_exist():
    profs, rules = pf.load(pf.Path("/nonexistent/x.toml"))
    assert profs["games"].power == "performance" and profs["night"].power == "low-power"
    assert rules


def test_user_file_changes_and_adds(tmp_path):
    f = tmp_path / "p.toml"
    f.write_text('''
[profiles.games]
power = "balanced"
camera = false
[profiles.movie]
name = "Кино"
power = "low-power"
[[rules]]
profile = "movie"
processes = ["mpv"]
''')
    profs, rules = pf.load(f)
    assert profs["games"].power == "balanced" and profs["games"].camera is False
    assert profs["movie"].name == "Кино"
    assert [r.profile for r in rules] == ["movie"]


def test_bad_values_are_ignored(tmp_path):
    f = tmp_path / "p.toml"
    f.write_text('''
[profiles.games]
power = "turbo; rm -rf /"
camera = "yes"
[[rules]]
profile = "nope"
processes = ["x"]
[[rules]]
profile = "games"
''')
    profs, rules = pf.load(f)
    assert profs["games"].power == "performance" and profs["games"].camera is None
    assert rules == []  # unknown profile and empty rule are dropped


def test_broken_file_gives_defaults(tmp_path):
    f = tmp_path / "p.toml"
    f.write_text("this is [[ not toml")
    profs, rules = pf.load(f)
    assert set(profs) >= {"games", "work", "night"} and rules


def test_choose_rules_first_match_wins():
    rules = [pf.Rule("games", ["steam_app_*"]), pf.Rule("work", [], when="battery")]
    assert pf.choose(rules, {"steam_app_730", "bash"}, True) == "games"
    assert pf.choose(rules, {"steam_app_730"}, False) == "games"
    assert pf.choose(rules, {"bash"}, False) == "work"
    assert pf.choose(rules, {"bash"}, True) is None
    assert pf.choose(rules, {"bash"}, None) is None  # unknown adapter: do nothing


def test_apply_sends_only_what_profile_sets():
    sent = []

    def ask(req):
        sent.append(req)
        return {"profile": req["value"]} if req["action"] == "set_power_profile" else {"cameras": []}

    pf.apply(pf.Profile("a", "A", power="balanced"), ask)
    assert sent == [{"action": "set_power_profile", "value": "balanced"}]
    sent.clear()
    pf.apply(pf.Profile("b", "B", camera=False), ask)
    assert sent == [{"action": "set_camera", "value": False}]


def test_apply_reports_failure():
    lines = pf.apply(pf.Profile("a", "A", power="balanced"), lambda r: None)
    assert "не удалось" in lines[0]
