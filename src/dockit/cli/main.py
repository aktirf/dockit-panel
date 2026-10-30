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


def _ask_service(payload: dict) -> dict | None:
    """Send a request to the service. Print a clear message and return None on failure."""
    from ..daemon.client import DaemonUnavailable, request

    try:
        response = request(payload)
    except DaemonUnavailable:
        print("Служба DOCKIT не запущена. Установите её: sudo scripts/install-dev.sh")
        return None
    if not response.get("ok"):
        print("Отказано: " + str(response.get("error", "неизвестная ошибка")))
        return None
    return response.get("result", {})


def cmd_daemon(args: argparse.Namespace) -> int:
    import os

    from ..daemon import server
    from ..daemon.protocol import SOCKET_PATH

    if os.geteuid() != 0:
        print("Служба должна работать от root (её запускает systemd). "
              "Для обычной установки используйте scripts/install-dev.sh.")
        return 1
    server.run(args.socket or SOCKET_PATH)
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    from ..daemon.actions import CHOICES, PROFILE
    from ..core import sysfs

    if args.value is None:
        current = sysfs.read_text(PROFILE)
        if current is None:
            print("Режимы мощности не поддерживаются на этой модели.")
            return 1
        print(f"Сейчас: {current}")
        print("Доступно: " + (sysfs.read_text(CHOICES) or "?"))
        return 0
    result = _ask_service({"action": "set_power_profile", "value": args.value})
    if result is None:
        return 1
    print(f"Режим мощности: {result.get('profile')}")
    return 0


def cmd_camera(args: argparse.Namespace) -> int:
    from ..daemon.actions import camera_state

    if args.state == "status":
        cams = camera_state()["cameras"]
        if not cams:
            print("Камера не найдена среди известных устройств.")
            return 1
        for c in cams:
            print(f"{c['usb_id']}  {'включена' if c['enabled'] else 'выключена'}")
        return 0
    result = _ask_service({"action": "set_camera", "value": args.state == "on"})
    if result is None:
        return 1
    for c in result.get("cameras", []):
        print(f"{c['usb_id']}  {'включена' if c['enabled'] else 'выключена'}")
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

    p_daemon = sub.add_parser("daemon", help="run the root service (started by systemd)")
    p_daemon.add_argument("--socket", help="socket path, for tests")
    p_daemon.set_defaults(func=cmd_daemon)

    p_profile = sub.add_parser("profile", help="show or change the performance mode")
    p_profile.add_argument("value", nargs="?", help="low-power, balanced or performance")
    p_profile.set_defaults(func=cmd_profile)

    p_camera = sub.add_parser("camera", help="camera status, on or off")
    p_camera.add_argument("state", choices=["status", "on", "off"])
    p_camera.set_defaults(func=cmd_camera)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
