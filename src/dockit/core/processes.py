"""List of programs the user is running, to suggest names for profile rules."""

from __future__ import annotations

import fnmatch
import os

# system and desktop helpers nobody wants to build a rule on
NOISE = [
    "systemd*", "(sd-pam)", "dbus*", "pipewire*", "wireplumber", "xdg-*", "at-spi*", "gvfs*",
    "gnome-keyring*", "polkit*", "xwayland*", "Xwayland", "ssh-agent", "swayidle", "dgop",
    "dms*", "niri", "quickshell", "bash", "zsh", "fish", "sh", "sudo", "login", "python*",
    "dockit*", "kitty", "kded*", "kwalletd*", "fcitx*", "ibus*", "upowerd", "udisks*", "agetty",
    "ps", "tee", "sleep", "cat", "less", "ls", "(sd-*", "gpg-agent", "dconf-service", "tmux*",
    "Web Content*", "Socket Process", "Privileged Cont*", "Isolated *", "RDD Process",
    "Utility Process", "WebExtensions", "Web Co*", "forkserver", "crashhelper*", "*-wrapped",
    "bluetoothd", "obex*", "rtkit*", "nm-*", "NetworkManager", "gcr-*", "pkexec", "mako", "dunst",
]


def user_programs(uid: int | None = None, proc: str = "/proc") -> list[str]:
    """Distinct names of this user's running programs, without system helpers."""
    uid = os.getuid() if uid is None else uid
    names: set[str] = set()
    try:
        entries = os.listdir(proc)
    except OSError:
        return []
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(f"{proc}/{entry}/status", encoding="utf-8") as f:
                owner = next((line.split()[1] for line in f if line.startswith("Uid:")), "")
            if owner != str(uid):
                continue
            with open(f"{proc}/{entry}/comm", encoding="utf-8") as f:
                name = f.read().strip()
        except (OSError, IndexError):
            continue
        if name and not any(fnmatch.fnmatchcase(name, pattern) for pattern in NOISE):
            names.add(name)
    return sorted(names, key=str.lower)


# short plain-language descriptions shown as hints in the window
KNOWN = {
    "steam": "Steam — магазин и запуск игр.",
    "steamwebhelper": "Встроенный браузер Steam (часть Steam).",
    "cs2": "Counter-Strike 2.",
    "gamescope": "Gamescope — оболочка для запуска игр с настройкой кадров и разрешения.",
    "gamemoded": "GameMode — подстраивает систему под игру.",
    "lutris": "Lutris — запуск игр и эмуляторов.",
    "heroic": "Heroic — запуск игр из Epic и GOG.",
    "wine*": "Wine — запуск Windows-программ и игр.",
    "proton*": "Proton — запуск Windows-игр из Steam.",
    "firefox*": "Firefox — браузер.",
    "zen*": "Zen — браузер.",
    "chrome*": "Chrome — браузер.",
    "code*": "Редактор кода.",
    "discord*": "Discord — голосовой чат.",
    "telegram*": "Telegram — мессенджер.",
    "obs*": "OBS — запись и трансляция экрана.",
    "mpv": "mpv — видеоплеер.",
    "vlc": "VLC — видеоплеер.",
    "blender*": "Blender — 3D-редактор.",
}


def describe(name: str) -> str:
    """One line about a program: what it is, or how the rule will match it."""
    for pattern, text in KNOWN.items():
        if fnmatch.fnmatchcase(name.lower(), pattern):
            return text
    if "*" in name or "?" in name:
        return f"Шаблон: подойдёт любая программа с таким именем ({name})."
    if name.startswith("steam_app_"):
        return "Игра, запущенная через Steam."
    return f"Программа «{name}». Правило сработает, пока она запущена."


class TopCpu:
    """Which programs use the processor most. Call sample() regularly; shares are measured between calls."""

    def __init__(self, proc: str = "/proc", clock: float | None = None, now=None):
        import time
        self.proc = proc
        self._ticks = clock or float(os.sysconf("SC_CLK_TCK")) if hasattr(os, "sysconf") else 100.0
        self._time = now or time.monotonic
        self._last: dict[str, float] = {}
        self._last_at = self._time()

    def _read(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        try:
            entries = os.listdir(self.proc)
        except OSError:
            return totals
        for entry in entries:
            if not entry.isdigit():
                continue
            try:
                with open(f"{self.proc}/{entry}/stat", encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                continue
            start, end = text.find("("), text.rfind(")")
            if start < 0 or end < 0:
                continue
            fields = text[end + 2:].split()
            try:
                used = (int(fields[11]) + int(fields[12])) / self._ticks   # utime + stime, seconds
            except (IndexError, ValueError):
                continue
            name = text[start + 1:end]
            totals[name] = totals.get(name, 0.0) + used
        return totals

    def sample(self, count: int = 5) -> list[dict]:
        now = self._time()
        current = self._read()
        span = now - self._last_at
        result = []
        if span > 0 and self._last:
            for name, used in current.items():
                delta = used - self._last.get(name, used)
                if delta > 0:
                    result.append({"name": name, "cpu": round(100 * delta / span)})
        self._last, self._last_at = current, now
        result = [r for r in result if r["cpu"] >= 1]
        result.sort(key=lambda r: -r["cpu"])
        return result[:count]
