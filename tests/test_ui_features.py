from dockit.core import profiles as pf
from dockit.gui import tray


def test_next_profile_id_cycles_and_wraps():
    available = {
        "games": pf.Profile("games", "Игры"),
        "work": pf.Profile("work", "Работа"),
        "night": pf.Profile("night", "Ночь"),
    }
    assert pf.next_profile_id(available, "games") == "work"
    assert pf.next_profile_id(available, "work") == "night"
    assert pf.next_profile_id(available, "night") == "games"
    # Unknown or "auto" starts from the first profile.
    assert pf.next_profile_id(available, "auto") == "games"
    assert pf.next_profile_id(available, "") == "games"
    assert pf.next_profile_id({}, "games") is None


def test_tray_tooltip_formats_mode_and_temps():
    modes = {"low-power": "Тишина", "balanced": "Баланс", "performance": "Производительность"}
    tip = tray.format_tooltip(
        {"currentMode": "balanced", "cpu": {"temp": "48"}, "gpu": {"asleep": True, "temp": "—"}},
        modes,
    )
    assert tip == "DOCKIT · Баланс · CPU 48 °C · GPU спит"

    tip_awake = tray.format_tooltip(
        {"currentMode": "performance", "cpu": {"temp": "72"}, "gpu": {"asleep": False, "temp": "64"}},
        modes,
    )
    assert tip_awake == "DOCKIT · Производительность · CPU 72 °C · GPU 64 °C"

    assert tray.format_tooltip({}, modes) == "DOCKIT"
