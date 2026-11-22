from pathlib import Path

from dockit.core.scanner import ScanItem, ScanResult, collect_environment_details, format_report
from dockit.core.status import Status


def test_markdown_report_contains_details_and_no_personal_info():
    res = ScanResult(
        system={"vendor": "LENOVO", "model": "ThinkPad T14", "bios": "1.20", "kernel": "6.14.0", "distro": "Arch Linux"},
        items=[
            ScanItem("service", "Service", "systemd", Status.OK, "running"),
            ScanItem("battery_limit", "Charge limit", "power_supply", Status.OK, "80%"),
        ],
    )
    env = {
        "cpu": "AMD Ryzen 7 PRO 7840U",
        "cpu_driver": "amd-pstate-epp",
        "epp_choices": "default performance balance_performance balance_power power",
        "desktop": "KDE Plasma",
        "form_factor": "laptop",
        "display": "eDP-1 (120Hz; rates: 60Hz, 120Hz)",
        "battery_limit": "threshold=80%",
        "hwmon": "k10temp, nvme, thinkpad(1f)",
    }

    md = format_report(res, lang="en", markdown=True, env_details=env)
    assert "### DOCKIT report (`v" in md
    assert "| `cpu_driver` | amd-pstate-epp |" in md
    assert "| `battery_limit` | threshold=80% |" in md
    assert "<details>" in md and "</details>" in md
    assert "serial" not in md.lower()

    plain = format_report(res, lang="ru", markdown=False, env_details=env)
    assert "DOCKIT report" in plain
    assert "cpu_driver: amd-pstate-epp" in plain
    assert "display: eDP-1" in plain


def test_collect_environment_details_never_raises():
    details = collect_environment_details()
    assert isinstance(details, dict)
    assert "desktop" in details
    assert "form_factor" in details


def test_issue_templates_and_universal_probe_exist():
    root = Path(__file__).resolve().parents[1]
    dev_tpl = (root / ".github/ISSUE_TEMPLATE/device_report.md").read_text(encoding="utf-8")
    bug_tpl = (root / ".github/ISSUE_TEMPLATE/bug_report.md").read_text(encoding="utf-8")
    probe = (root / "scripts/probe.sh").read_text(encoding="utf-8")

    assert "dockit report" in dev_tpl
    assert "dockit report" in bug_tpl
    # Universal probe must not be hardcoded to one vendor's keyboard ID
    assert "0414:8104" not in probe
    # And must check suspended state before touching nvidia-smi
    assert "suspended" in probe
