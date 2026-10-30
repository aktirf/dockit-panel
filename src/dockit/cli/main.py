"""Command line: `dockit scan` and `dockit report`."""

from __future__ import annotations

import argparse
import json
import sys

from .. import __version__
from ..core.scanner import format_report, scan
from ..core.status import LABELS_RU, Status
from ..peripherals.scan import KIND_RU

ICONS = {
    Status.OK: "OK ",
    Status.NEEDS_SETUP: "SET",
    Status.NEEDS_ROOT: "ROOT",
    Status.UNAVAILABLE: "NO ",
}


def cmd_scan(args: argparse.Namespace) -> int:
    result = scan()
    if args.json:
        payload = {
            "system": result.system,
            "items": [
                {
                    "id": i.id,
                    "name": i.name,
                    "source": i.source,
                    "status": i.status.value,
                    "detail": i.detail,
                    "state": i.state,
                    "hint": i.hint,
                }
                for i in result.items
            ],
            "laptop_in_database": bool(result.laptop),
            "peripherals": [
                {
                    "usb_id": p.usb_id,
                    "name": p.name,
                    "kind": p.kind,
                    "known": p.known,
                    "status": p.status,
                    "features": p.features,
                }
                for p in result.peripherals
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"{result.system['vendor']} {result.system['model']}  |  {result.system['distro']}  |  {result.system['kernel']}")
    print()
    for item in result.items:
        print(f"[{ICONS[item.status]}] {item.name}: {LABELS_RU[item.status]}")
        print(f"       {item.detail}")
        if item.hint:
            print(f"       Как исправить: {item.hint}")

    if result.peripherals:
        print()
        print("Устройства USB:")
        for p in result.peripherals:
            kind = KIND_RU.get(p.kind, KIND_RU["unknown"])
            mark = "" if p.known else "  (нет в базе устройств)"
            print(f"  {p.usb_id}  {kind:<11} {p.name}{mark}")
    print()
    print("Ваш ноутбук в базе: " + ("да (" + result.laptop.status + ")" if result.laptop else "нет"))
    return 0


def cmd_report(_: argparse.Namespace) -> int:
    print(format_report(scan()))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dockit",
        description="DOCKIT: shows which laptop features work on this machine.",
    )
    parser.add_argument("--version", action="version", version=f"dockit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="check which features are available")
    p_scan.add_argument("--json", action="store_true", help="machine-readable output")
    p_scan.set_defaults(func=cmd_scan)

    p_report = sub.add_parser("report", help="print a text report for a GitHub issue")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
