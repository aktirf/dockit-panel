from pathlib import Path

from dockit.core import session_state as ss


def test_save_load_and_validation(tmp_path: Path):
    p = tmp_path / "session.json"
    assert ss.load(p) == {}
    assert ss.has_saved(p) is False

    saved = ss.save(
        {
            "refresh": 165,
            "power": "performance",
            "kbd_backlight": {"on": True, "brightness": 80, "color": "#5ab0ff", "autonomous": False},
        },
        path=p,
    )
    assert saved == {
        "refresh": 165,
        "power": "performance",
        "kbd_backlight": {"on": True, "brightness": 80, "color": "#5AB0FF", "autonomous": False},
    }
    assert ss.has_saved(p) is True
    assert ss.load(p) == saved

    # Invalid updates are ignored while valid existing keys are preserved
    after_bad = ss.save(
        {"refresh": 9999, "power": "turbo", "kbd_backlight": {"on": "yes"}},
        path=p,
    )
    assert after_bad == saved


def test_restore_applies_changed_values_quietly(tmp_path: Path):
    p = tmp_path / "session.json"
    ss.save(
        {
            "refresh": 60,
            "power": "low-power",
            "kbd_backlight": {"on": True, "brightness": 70, "color": "#00FF00", "autonomous": False},
        },
        path=p,
    )

    asked = []
    refreshed = []

    def fake_ask(payload):
        asked.append(payload)
        return {"ok": True}

    def fake_set_refresh(hz):
        refreshed.append(hz)
        return None

    applied = ss.restore(
        fake_ask,
        path=p,
        refresh_info_fn=lambda: {"current": 165, "rates": [60, 165]},
        set_refresh_fn=fake_set_refresh,
        current_power_fn=lambda: "balanced",
        discover_kbd_fn=lambda: [{"name": "GIGABYTE"}],
    )

    assert applied == ["power=low-power", "refresh=60Hz", "kbd_backlight"]
    assert refreshed == [60]
    assert len(asked) == 2
    assert all(req["interactive"] is False for req in asked)
    assert asked[0]["action"] == "set_power_profile" and asked[0]["value"] == "low-power"
    assert asked[1]["action"] == "set_kbd_backlight" and asked[1]["value"]["color"] == "#00FF00"


def test_restore_skips_matching_or_unsupported_values(tmp_path: Path):
    p = tmp_path / "session.json"
    ss.save(
        {
            "refresh": 144,  # not in [60, 165]
            "power": "balanced",  # already balanced
            "kbd_backlight": {"on": True, "brightness": 100, "color": "#FFFFFF", "autonomous": False},
        },
        path=p,
    )
    asked = []
    refreshed = []
    applied = ss.restore(
        lambda payload: asked.append(payload) or {},
        path=p,
        refresh_info_fn=lambda: {"current": 165, "rates": [60, 165]},
        set_refresh_fn=lambda hz: refreshed.append(hz) or None,
        current_power_fn=lambda: "balanced",
        discover_kbd_fn=lambda: [],
    )
    assert applied == []
    assert asked == []
    assert refreshed == []


def test_restore_auto_scenario_only_restores_kbd_backlight(tmp_path: Path):
    p = tmp_path / "session.json"
    ss.save(
        {
            "refresh": 60,
            "power": "low-power",
            "kbd_backlight": {"on": True, "brightness": 50, "color": "#FF0000", "autonomous": False},
        },
        path=p,
    )
    asked = []
    applied = ss.restore(
        lambda payload: asked.append(payload) or {},
        path=p,
        include_power_and_refresh=False,
        refresh_info_fn=lambda: {"current": 165, "rates": [60, 165]},
        set_refresh_fn=lambda hz: None,
        current_power_fn=lambda: "balanced",
        discover_kbd_fn=lambda: [{"name": "GIGABYTE"}],
    )
    assert applied == ["kbd_backlight"]
    assert len(asked) == 1 and asked[0]["action"] == "set_kbd_backlight"
