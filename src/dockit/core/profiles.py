"""Profiles (Games / Work / Night) and the rules that pick one automatically.

A profile is a named bundle of settings. Defaults are built in; the user can
change or add profiles in ~/.config/dockit/profiles.toml, for example:

    [profiles.games]
    power = "performance"

    [[rules]]
    profile = "games"
    processes = ["steam_app_*", "gamescope*"]

    [[rules]]
    profile = "work"
    when = "battery"

Rules are checked from top to bottom, the first one that matches wins.
"""

from __future__ import annotations

import fnmatch
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

POWER_VALUES = ("low-power", "balanced", "performance")


@dataclass
class Profile:
    id: str
    name: str
    power: str | None = None      # one of POWER_VALUES, or None = do not touch
    camera: bool | None = None    # True/False = switch, None = do not touch
    output: str | None = None     # part of a sound output name, e.g. "epos"
    input: str | None = None      # part of a microphone name


@dataclass
class Rule:
    profile: str
    processes: list[str]          # process name patterns, "*" allowed
    when: str = ""                # "", "battery" or "ac"


DEFAULT_PROFILES = {
    "games": Profile("games", "Игры", power="performance"),
    "work": Profile("work", "Работа", power="balanced"),
    "night": Profile("night", "Ночь", power="low-power"),
}

DEFAULT_RULES = [
    Rule("games", ["steam_app_*", "gamescope*"]),
    Rule("work", [], when="battery"),
]


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "dockit" / "profiles.toml"


def load(path: Path | None = None) -> tuple[dict[str, Profile], list[Rule]]:
    """Built-in profiles and rules, changed by the user's file if there is one.

    A broken or missing file never breaks the program: defaults are used.
    """
    profiles = {k: Profile(**vars(v)) for k, v in DEFAULT_PROFILES.items()}
    rules = list(DEFAULT_RULES)
    path = path or config_path()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return profiles, rules

    custom = data.get("profiles", {})
    if isinstance(custom, dict):
        for pid, body in custom.items():
            if not isinstance(body, dict) or not _safe_id(pid):
                continue
            base = profiles.get(pid) or Profile(pid, str(body.get("name", pid)))
            power = body.get("power", base.power)
            camera = body.get("camera", base.camera)
            out = body.get("output", base.output)
            mic = body.get("input", base.input)
            profiles[pid] = Profile(
                pid,
                str(body.get("name", base.name)),
                power if power in POWER_VALUES else base.power,
                camera if isinstance(camera, bool) else base.camera,
                out if isinstance(out, str) and out.strip() else base.output,
                mic if isinstance(mic, str) and mic.strip() else base.input,
            )

    custom_rules = data.get("rules")
    if isinstance(custom_rules, list):
        parsed = []
        for body in custom_rules:
            if not isinstance(body, dict):
                continue
            procs = body.get("processes", [])
            when = body.get("when", "")
            if (body.get("profile") in profiles and isinstance(procs, list)
                    and when in ("", "battery", "ac") and (procs or when)):
                parsed.append(Rule(body["profile"], [str(p) for p in procs], when))
        rules = parsed
    return profiles, rules


def _safe_id(text: object) -> bool:
    return isinstance(text, str) and text.isidentifier()


def running_processes() -> set[str]:
    names = set()
    try:
        entries = os.listdir("/proc")
    except OSError:
        return names
    for entry in entries:
        if entry.isdigit():
            try:
                with open(f"/proc/{entry}/comm", encoding="utf-8") as f:
                    names.add(f.read().strip())
            except OSError:
                continue
    return names


def choose(rules: list[Rule], processes: set[str], on_ac: bool | None) -> str | None:
    """Id of the profile that should be active now, or None if no rule matches."""
    for rule in rules:
        if rule.when == "battery" and on_ac is not False:
            continue
        if rule.when == "ac" and on_ac is not True:
            continue
        if rule.processes and not any(
            fnmatch.fnmatchcase(name, pattern) for name in processes for pattern in rule.processes
        ):
            continue
        return rule.profile
    return None


def apply(profile: Profile, ask: Callable[[dict], dict | None]) -> list[str]:
    """Send the profile's settings to the service. Returns lines for the user."""
    lines = []
    if profile.power:
        result = ask({"action": "set_power_profile", "value": profile.power})
        lines.append(f"Режим мощности: {result['profile']}" if result else "Режим мощности: не удалось")
    if profile.camera is not None:
        result = ask({"action": "set_camera", "value": profile.camera})
        lines.append("Камера: " + ("включена" if profile.camera else "выключена") if result is not None
                     else "Камера: не удалось")
    for kind, query in (("output", profile.output), ("input", profile.input)):
        if not query:
            continue
        from . import audio  # imported here: profile logic works without sound tools

        label = "Звук (вывод)" if kind == "output" else "Микрофон"
        try:
            device = audio.set_default(kind, query)
            lines.append(f"{label}: {device.description}")
        except audio.AudioError as exc:
            lines.append(f"{label}: {exc}")
    return lines
