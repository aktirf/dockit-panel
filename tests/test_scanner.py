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
