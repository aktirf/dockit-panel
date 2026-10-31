"""Processor load and frequency (read only, from /proc and sysfs)."""

from __future__ import annotations

import glob
import os

from . import sysfs


class CpuMonitor:
    """Call sample() from time to time; load is measured between two calls."""

    def __init__(self, stat: str = "/proc/stat", cpu_dir: str = "/sys/devices/system/cpu",
                 cpuinfo: str = "/proc/cpuinfo"):
        self.stat = stat
        self.cpu_dir = cpu_dir
        self.cpuinfo = cpuinfo
        self._last = self._read_stat()

    def _read_stat(self) -> tuple[int, int] | None:
        text = sysfs.read_text(self.stat)
        if not text:
            return None
        parts = text.splitlines()[0].split()
        if not parts or parts[0] != "cpu":
            return None
        try:
            numbers = [int(x) for x in parts[1:9]]
        except ValueError:
            return None
        idle = numbers[3] + (numbers[4] if len(numbers) > 4 else 0)
        return sum(numbers), idle

    def name(self) -> str:
        text = sysfs.read_text(self.cpuinfo) or ""
        for line in text.splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
        return ""

    def frequency_mhz(self) -> int | None:
        values = []
        for f in glob.glob(os.path.join(self.cpu_dir, "cpu[0-9]*", "cpufreq", "scaling_cur_freq")):
            raw = sysfs.read_text(f)
            if raw and raw.isdigit():
                values.append(int(raw))
        return round(sum(values) / len(values) / 1000) if values else None

    def sample(self) -> dict:
        now = self._read_stat()
        load = None
        if now and self._last:
            total = now[0] - self._last[0]
            idle = now[1] - self._last[1]
            if total > 0:
                load = max(0, min(100, round(100 * (1 - idle / total))))
        if now:
            self._last = now
        return {"load_pct": load, "freq_mhz": self.frequency_mhz()}
