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
