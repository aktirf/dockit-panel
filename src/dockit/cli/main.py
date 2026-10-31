"""Command line: `dockit scan` and `dockit report`."""

from __future__ import annotations

import argparse
import json
import sys

from .. import __version__
from ..core.scanner import display_name, format_report, scan
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

    print(f"{display_name(result.system)}  |  {result.system['distro']}  |  {result.system['kernel']}")
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


def cmd_mode(args: argparse.Namespace) -> int:
    from ..core import profiles as pf

    available, rules = pf.load()
    if args.name is None:
        from ..core import sysfs
        from ..daemon.actions import PROFILE

        print("Профили:")
        for p in available.values():
            extra = []
            if p.power:
                extra.append(f"мощность {p.power}")
            if p.camera is not None:
                extra.append("камера " + ("вкл" if p.camera else "выкл"))
            if p.output:
                extra.append(f"звук «{p.output}»")
            if p.input:
                extra.append(f"микрофон «{p.input}»")
            print(f"  {p.id:<8} {p.name:<8} {', '.join(extra)}")
        print(f"Сейчас режим мощности: {sysfs.read_text(PROFILE) or '?'}")
        return 0
    profile = available.get(args.name)
    if profile is None:
        print("Нет такого профиля. Список: dockit mode")
        return 1
    for line in pf.apply(profile, _ask_service):
        print(line)
    return 0


def cmd_auto(args: argparse.Namespace) -> int:
    import time

    from ..core import profiles as pf
    from ..modules.battery import ac_online

    current = None
    while True:
        available, rules = pf.load()  # re-read so edits to the file take effect
        wanted = pf.choose(rules, pf.running_processes(), ac_online())
        if wanted and wanted != current:
            print(f"Профиль: {available[wanted].name}", flush=True)
            for line in pf.apply(available[wanted], _ask_service):
                print("  " + line, flush=True)
            current = wanted
        if args.once:
            return 0
        time.sleep(max(2, args.interval))


def cmd_audio(args: argparse.Namespace) -> int:
    from ..core import audio

    try:
        if args.action == "status":
            for d in audio.list_devices():
                mark = "*" if d.default else " "
                kind = "вывод " if d.kind == "output" else "микрофон"
                vol = f"{d.volume}%" if d.volume is not None else "?"
                muted = "  (выключен)" if d.muted else ""
                print(f" {mark} {kind:<8} {d.description}  громкость {vol}{muted}")
            return 0
        if args.action in ("output", "input"):
            if not args.value:
                print(f"Укажите часть названия, например: dockit audio {args.action} epos")
                return 1
            device = audio.set_default(args.action, args.value)
            print(f"Выбрано: {device.description}")
            return 0
        if args.action == "mic":
            if args.value not in ("mute", "unmute"):
                print("Укажите: dockit audio mic mute  или  dockit audio mic unmute")
                return 1
            audio.set_mute("input", args.value == "mute")
            print("Микрофон выключен" if args.value == "mute" else "Микрофон включён")
            return 0
        if args.action == "volume":
            if not args.value or not args.value.isdigit():
                print("Укажите число от 0 до 150, например: dockit audio volume 50")
                return 1
            audio.set_volume("output", int(args.value))
            print(f"Громкость: {args.value}%")
            return 0
    except audio.AudioError as exc:
        print(str(exc))
        return 1
    return 1


def cmd_gui(_: argparse.Namespace) -> int:
    from ..gui.app import run

    return run()


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

    p_mode = sub.add_parser("mode", help="list profiles or switch to one (games, work, night)")
    p_mode.add_argument("name", nargs="?")
    p_mode.set_defaults(func=cmd_mode)

    p_auto = sub.add_parser("auto", help="switch profiles automatically by the rules")
    p_auto.add_argument("--once", action="store_true", help="check once and exit")
    p_auto.add_argument("--interval", type=int, default=5, help="seconds between checks")
    p_auto.set_defaults(func=cmd_auto)

    p_audio = sub.add_parser("audio", help="sound: status, output, input, mic, volume")
    p_audio.add_argument("action", nargs="?", default="status",
                         choices=["status", "output", "input", "mic", "volume"])
    p_audio.add_argument("value", nargs="?")
    p_audio.set_defaults(func=cmd_audio)

    p_gui = sub.add_parser("gui", help="open the window")
    p_gui.set_defaults(func=cmd_gui)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
