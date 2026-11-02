"""Processor tuning (Turbo Boost, energy preference) and the video card power limit."""

from __future__ import annotations

import glob
import shutil
import subprocess

from . import sysfs

CPU = "/sys/devices/system/cpu"


def boost_path(base: str = CPU) -> str:
    return f"{base}/cpufreq/boost"


def read_boost(base: str = CPU) -> bool | None:
    raw = sysfs.read_text(boost_path(base))
    return None if raw not in ("0", "1") else raw == "1"


def epp_files(base: str = CPU) -> list[str]:
    return sorted(glob.glob(f"{base}/cpu[0-9]*/cpufreq/energy_performance_preference"))


def epp_choices(base: str = CPU) -> list[str]:
    raw = sysfs.read_text(f"{base}/cpu0/cpufreq/energy_performance_available_preferences")
    return raw.split() if raw else []


def read_epp(base: str = CPU) -> str | None:
    return sysfs.read_text(f"{base}/cpu0/cpufreq/energy_performance_preference")


def gpu_power_limits() -> dict | None:
    """{"current","min","max"} in watts, or None when the driver does not allow changing it."""
    tool = shutil.which("nvidia-smi")
    if tool is None:
        return None
    try:
        proc = subprocess.run([tool, "--query-gpu=power.limit,power.min_limit,power.max_limit",
                               "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        cur, lo, hi = (float(x) for x in proc.stdout.strip().splitlines()[0].split(","))
    except ValueError:
        return None
    if hi <= lo:
        return None      # laptop cards often have a fixed limit
    return {"current": round(cur), "min": round(lo), "max": round(hi)}
