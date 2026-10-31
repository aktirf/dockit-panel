from dockit.core.scanner import format_report, scan
from dockit.core.status import Status
from dockit.modules import ALL_MODULES


def test_scan_returns_item_for_every_module():
    result = scan()
    assert len(result.items) == len(ALL_MODULES)
    assert all(isinstance(i.status, Status) for i in result.items)


def test_scan_survives_broken_module():
    class Broken:
        id = "broken"
        name = "Broken"
        source = "none"

        def detect(self):
            raise RuntimeError("boom")

    result = scan([Broken])
    assert result.items[0].status is Status.UNAVAILABLE


def test_report_has_no_serial_or_hostname():
    text = format_report(scan())
    assert "DOCKIT report" in text
    assert "serial" not in text.lower()


def test_display_name_does_not_repeat_vendor():
    from dockit.core.scanner import display_name

    assert display_name({"vendor": "GIGABYTE", "model": "GIGABYTE GAMING A16 3VH"}) == "GIGABYTE GAMING A16 3VH"
    assert display_name({"vendor": "ASUS", "model": "TUF A15"}) == "ASUS TUF A15"


def test_wireless_is_on_if_any_switch_of_that_kind_is_on(tmp_path, monkeypatch):
    from dockit.modules import wireless

    def rf(name, kind, soft, hard):
        d = tmp_path / name
        d.mkdir()
        (d / "type").write_text(kind + "\n")
        (d / "soft").write_text(soft + "\n")
        (d / "hard").write_text(hard + "\n")

    rf("rfkill0", "wlan", "0", "0")
    rf("rfkill1", "wlan", "1", "0")   # a second, blocked switch must not hide the working one
    rf("rfkill2", "bluetooth", "1", "0")
    monkeypatch.setattr(wireless, "RFKILL", str(tmp_path))
    assert wireless._read_all() == {"wlan": True, "bluetooth": False}
