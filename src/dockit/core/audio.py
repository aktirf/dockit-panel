"""Sound devices through PipeWire/PulseAudio (the `pactl` command).

Everything here runs as the normal user, no root service is needed.
The command runner is passed in so tests can use fake output.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable

Runner = Callable[[list[str]], str]


class AudioError(Exception):
    pass


@dataclass
class AudioDevice:
    kind: str            # "output" or "input"
    name: str            # technical name, used for switching
    description: str     # what the user sees
    volume: int | None   # percent, None if unknown
    muted: bool
    default: bool


def run_pactl(args: list[str]) -> str:
    if shutil.which("pactl") is None:
        raise AudioError("Нет команды pactl (пакет libpulse) или не запущен PipeWire.")
    try:
        proc = subprocess.run(["pactl", *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AudioError("Звуковая система не отвечает.") from exc
    if proc.returncode != 0:
        raise AudioError("Звуковая система вернула ошибку.")
    return proc.stdout


def _percent(item: dict) -> int | None:
    values = []
    volume = item.get("volume")
    if isinstance(volume, dict):
        for channel in volume.values():
            text = channel.get("value_percent") if isinstance(channel, dict) else None
            if isinstance(text, str) and text.rstrip("%").isdigit():
                values.append(int(text.rstrip("%")))
    return max(values) if values else None


def list_devices(run: Runner = run_pactl) -> list[AudioDevice]:
    devices: list[AudioDevice] = []
    for kind, listing, getter in (
        ("output", "sinks", "get-default-sink"),
        ("input", "sources", "get-default-source"),
    ):
        try:
            items = json.loads(run(["-f", "json", "list", listing]))
        except ValueError as exc:
            raise AudioError("Не удалось разобрать ответ звуковой системы.") from exc
        default = run([getter]).strip()
        for item in items if isinstance(items, list) else []:
            name = item.get("name")
            if not isinstance(name, str) or name.endswith(".monitor"):
                continue  # monitors are copies of outputs, not real microphones
            devices.append(AudioDevice(
                kind=kind,
                name=name,
                description=str(item.get("description") or name),
                volume=_percent(item),
                muted=bool(item.get("mute")),
                default=name == default,
            ))
    return devices


def find(devices: list[AudioDevice], kind: str, query: str) -> AudioDevice | None:
    """Find a device by part of its name, ignoring case (e.g. "epos")."""
    wanted = query.strip().lower()
    if not wanted:
        return None
    for d in devices:
        if d.kind == kind and wanted in d.description.lower():
            return d
    for d in devices:
        if d.kind == kind and wanted in d.name.lower():
            return d
    return None


def _target(kind: str) -> tuple[str, str]:
    if kind == "output":
        return "sink", "@DEFAULT_SINK@"
    if kind == "input":
        return "source", "@DEFAULT_SOURCE@"
    raise AudioError("Неизвестный тип устройства.")


def set_default(kind: str, query: str, run: Runner = run_pactl) -> AudioDevice:
    device = find(list_devices(run), kind, query)
    if device is None:
        raise AudioError(f"Устройство «{query}» не найдено.")
    word, _ = _target(kind)
    run([f"set-default-{word}", device.name])  # name comes from the system list, not from the user
    return device


def set_mute(kind: str, muted: bool, run: Runner = run_pactl) -> None:
    word, default = _target(kind)
    run([f"set-{word}-mute", default, "1" if muted else "0"])


def set_volume(kind: str, percent: int, run: Runner = run_pactl) -> None:
    if not isinstance(percent, int) or isinstance(percent, bool) or not 0 <= percent <= 150:
        raise AudioError("Громкость должна быть числом от 0 до 150.")
    word, default = _target(kind)
    run([f"set-{word}-volume", default, f"{percent}%"])
