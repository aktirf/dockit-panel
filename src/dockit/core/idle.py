"""Detects "no keyboard or mouse activity for N minutes" on Wayland.

It runs `swayidle` (a small separate program, `sudo pacman -S swayidle`),
which tells us through flag files when each waiting time has passed. Idle
inhibitors (a video playing, for example) are respected by the compositor.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path


def available() -> bool:
    return shutil.which("swayidle") is not None


def flag_dir() -> Path:
    base = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/dockit-{os.getuid()}"
    return Path(base) / "dockit-idle"


def swayidle_command(minutes: list[int], directory: Path) -> list[str]:
    command = ["swayidle", "-w"]
    for m in minutes:
        flag = shlex.quote(str(directory / str(m)))
        command += ["timeout", str(m * 60), f"touch {flag}", "resume", f"rm -f {flag}"]
    return command


class IdleWatcher:
    """Keeps one swayidle running for the given waiting times."""

    def __init__(self) -> None:
        self._minutes: list[int] = []
        self._proc: subprocess.Popen | None = None
        self.directory = flag_dir()

    def set_minutes(self, minutes: list[int]) -> None:
        minutes = sorted({m for m in minutes if isinstance(m, int) and 0 < m <= 1440})
        if minutes == self._minutes and self._proc is not None and self._proc.poll() is None:
            return
        self.stop()
        self._minutes = minutes
        if not minutes or not available():
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        for old in self.directory.glob("*"):
            old.unlink(missing_ok=True)
        self._proc = subprocess.Popen(
            swayidle_command(minutes, self.directory),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def reached(self) -> set[int]:
        return {m for m in self._minutes if (self.directory / str(m)).exists()}

    def stop(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None
        self._minutes = []
        for old in self.directory.glob("*"):
            old.unlink(missing_ok=True)
