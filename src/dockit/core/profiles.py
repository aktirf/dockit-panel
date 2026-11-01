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
A rule may also say "idle_minutes = 15": it matches after that many minutes
without keyboard or mouse activity. When no rule matches, the profile named
by the top-level key `fallback` is used (default "work"; "keep" = do nothing).
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

POWER_VALUES = ("low-power", "balanced", "performance")
IDLE_CHOICES = (5, 10, 15, 30, 60)   # what the window offers; the file may use any 1-1440
MAX_PROCESSES = 20


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
    idle: int = 0                 # minutes without activity, 0 = not used


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


_MISSING = object()
KEEP = "keep"   # written in the file when a profile must not touch a setting


def _power(value, base):
    if value is _MISSING:
        return base
    if value == KEEP:
        return None
    return value if value in POWER_VALUES else base


def _camera(value, base):
    if value is _MISSING:
        return base
    if value == KEEP:
        return None
    return value if isinstance(value, bool) else base


def _text(value, base):
    if value is _MISSING or not isinstance(value, str):
        return base
    value = value.strip()
    return value or None   # an empty text means: do not touch


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
            profiles[pid] = Profile(
                pid,
                str(body.get("name", base.name)),
                _power(body.get("power", _MISSING), base.power),
                _camera(body.get("camera", _MISSING), base.camera),
                _text(body.get("output", _MISSING), base.output),
                _text(body.get("input", _MISSING), base.input),
            )

    custom_rules = data.get("rules")
    if isinstance(custom_rules, list):
        parsed = []
        for body in custom_rules:
            if not isinstance(body, dict):
                continue
            rule = _parse_rule(body, profiles)
            if rule is not None:
                parsed.append(rule)
        rules = parsed
    return profiles, rules


def _parse_rule(body: dict, profiles: dict) -> Rule | None:
    procs = body.get("processes", [])
    when = body.get("when", "")
    idle = body.get("idle_minutes", 0)
    if body.get("profile") not in profiles or not isinstance(procs, list):
        return None
    if when not in ("", "battery", "ac"):
        return None
    if isinstance(idle, bool) or not isinstance(idle, int) or not 0 <= idle <= 1440:
        return None
    procs = [str(p) for p in procs][:MAX_PROCESSES]
    if not (procs or when or idle):
        return None
    return Rule(body["profile"], procs, when, idle)


def load_fallback(path: Path | None = None) -> str | None:
    """Profile id used when no rule matches (None = leave things as they are)."""
    path = path or config_path()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "work"
    value = data.get("fallback", "work")
    if not isinstance(value, str) or value in (KEEP, ""):
        return None
    return value if value.isidentifier() else "work"


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


def choose(rules: list[Rule], processes: set[str], on_ac: bool | None,
           idle_reached: set[int] | frozenset = frozenset()) -> str | None:
    """Id of the profile that should be active now, or None if no rule matches.

    idle_reached: the "idle_minutes" values of rules whose waiting time has passed.
    """
    for rule in rules:
        if rule.idle and rule.idle not in idle_reached:
            continue
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


def _toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)   # JSON strings are valid TOML strings


def _dump(data: dict) -> str:
    lines = ["# DOCKIT profiles. The window rewrites this file when you change a profile.", ""]
    for key, value in data.items():
        if not isinstance(value, (dict, list)):
            lines.append(f"{key} = {_toml_value(value)}")
    if len(lines) > 2:
        lines.append("")
    for pid, body in data.get("profiles", {}).items():
        lines.append(f"[profiles.{pid}]")
        lines += [f"{key} = {_toml_value(value)}" for key, value in body.items()]
        lines.append("")
    for rule in data.get("rules", []):
        lines.append("[[rules]]")
        lines += [f"{key} = {_toml_value(value)}" for key, value in rule.items()]
        lines.append("")
    return "\n".join(lines)


def save_profile(pid: str, power: str, camera: str, output: str, mic: str,
                 path: Path | None = None) -> None:
    """Store the four settings of one profile in the user's file (other content stays).

    power: "keep" or a power mode; camera: "keep", "on" or "off";
    output, mic: part of a device name, or "" to leave it alone.
    """
    if not _safe_id(pid):
        raise ValueError("bad profile id")
    if power != KEEP and power not in POWER_VALUES:
        raise ValueError("bad power mode")
    if camera not in (KEEP, "on", "off"):
        raise ValueError("bad camera value")
    if len(output) > 200 or len(mic) > 200:
        raise ValueError("text too long")
    path = path or config_path()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    section = data.setdefault("profiles", {})
    body = dict(section.get(pid, {})) if isinstance(section.get(pid), dict) else {}
    body["power"] = power
    body["camera"] = KEEP if camera == KEEP else camera == "on"
    body["output"] = output.strip()
    body["input"] = mic.strip()
    section[pid] = body
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(_dump(data), encoding="utf-8")
    temp.replace(path)


PROCESS_NAME = re.compile(r"^[\w.+*?-]{1,64}$")


def clean_processes(names: list[str]) -> list[str]:
    """Keep only sane process-name patterns, without repeats, at most MAX_PROCESSES."""
    result: list[str] = []
    for name in names:
        name = name.strip()
        if PROCESS_NAME.match(name) and name not in result:
            result.append(name)
    return result[:MAX_PROCESSES]


def save_rule(pid: str, processes: list[str], when: str, idle: int, path: Path | None = None) -> None:
    """Make `pid` have exactly one rule with these conditions (all of them must hold).

    Other profiles' rules and their order stay as they are. If the file had no
    rules yet, the built-in ones are written out first so they are not lost.
    """
    if not _safe_id(pid):
        raise ValueError("bad profile id")
    if when not in ("", "battery", "ac"):
        raise ValueError("bad condition")
    if isinstance(idle, bool) or not isinstance(idle, int) or not 0 <= idle <= 1440:
        raise ValueError("bad idle time")
    processes = clean_processes(processes)
    path = path or config_path()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    _, current = load(path)
    new_rule = {"profile": pid}
    if processes:
        new_rule["processes"] = processes
    if when:
        new_rule["when"] = when
    if idle:
        new_rule["idle_minutes"] = idle
    rules_out: list[dict] = []
    placed = False
    for rule in current:
        if rule.profile == pid:
            if not placed and len(new_rule) > 1:
                rules_out.append(new_rule)
                placed = True
            continue
        item: dict = {"profile": rule.profile}
        if rule.processes:
            item["processes"] = rule.processes
        if rule.when:
            item["when"] = rule.when
        if rule.idle:
            item["idle_minutes"] = rule.idle
        rules_out.append(item)
    if not placed and len(new_rule) > 1:
        rules_out.append(new_rule)
    data["rules"] = rules_out
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(_dump(data), encoding="utf-8")
    temp.replace(path)


def save_fallback(value: str, path: Path | None = None) -> None:
    """Which profile is used when no rule matches: a profile id or "keep" (do nothing)."""
    if value != KEEP and not _safe_id(value):
        raise ValueError("bad profile id")
    path = path or config_path()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data["fallback"] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(_dump(data), encoding="utf-8")
    temp.replace(path)


def _state_file() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return Path(base) / "dockit" / "scenario"


def load_scenario(path: Path | None = None) -> str:
    """The scenario chosen last time in the window ("" if none)."""
    try:
        value = (path or _state_file()).read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return value if value == "auto" or value.isidentifier() else ""


def save_scenario(value: str, path: Path | None = None) -> None:
    if value != "auto" and not (value.isidentifier()):
        return
    path = path or _state_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value + "\n", encoding="utf-8")
    except OSError:
        pass  # remembering the choice is a convenience, never an error
