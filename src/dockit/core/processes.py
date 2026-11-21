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


# short plain-language descriptions shown as hints in the window (keys in i18n locales)
KNOWN_KEYS = {
    "steam": "proc_desc_steam",
    "steamwebhelper": "proc_desc_steamwebhelper",
    "cs2": "proc_desc_cs2",
    "gamescope": "proc_desc_gamescope",
    "gamemoded": "proc_desc_gamemoded",
    "lutris": "proc_desc_lutris",
    "heroic": "proc_desc_heroic",
    "wine*": "proc_desc_wine",
    "proton*": "proc_desc_proton",
    "firefox*": "proc_desc_firefox",
    "zen*": "proc_desc_zen",
    "chrome*": "proc_desc_chrome",
    "code*": "proc_desc_code",
    "discord*": "proc_desc_discord",
    "telegram*": "proc_desc_telegram",
    "obs*": "proc_desc_obs",
    "mpv": "proc_desc_mpv",
    "vlc": "proc_desc_vlc",
    "blender*": "proc_desc_blender",
}


def describe(name: str, lang: str = "ru") -> str:
    """One line about a program: what it is, or how the rule will match it."""
    from . import i18n

    low = name.lower()
    for pattern, key in KNOWN_KEYS.items():
        if fnmatch.fnmatchcase(low, pattern):
            return i18n.tr(key, lang)
    if "*" in name or "?" in name:
        return i18n.tr("proc_desc_wildcard", lang, name=name)
    if name.startswith("steam_app_"):
        return i18n.tr("proc_desc_steam_game", lang)
    return i18n.tr("proc_desc_generic", lang, name=name)


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
