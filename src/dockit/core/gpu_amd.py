"""AMD Radeon GPU monitoring via Linux `amdgpu` sysfs (zero external tools).

Reads temperature, utilization, VRAM usage, power draw, clock speed, and D3 sleep
status directly from /sys/bus/pci/devices/* for AMD display cards (vendor 0x1002).
"""

from __future__ import annotations

import glob
import os

from . import sysfs

PCI = "/sys/bus/pci/devices"
AMD_VENDOR = "0x1002"


def _int(text: str | None) -> int | None:
    if text is None:
        return None
    s = text.strip()
    try:
        return int(s)
    except ValueError:
        return None


def _parse_active_sclk_mhz(text: str | None) -> int | None:
    """Parse `pp_dpm_sclk` active line like '1: 1850Mhz *' -> 1850."""
    if not text:
        return None
    for line in text.splitlines():
        if "*" not in line:
            continue
        for token in line.split():
            low = token.lower()
            if low.endswith("mhz"):
                val = _int(low[:-3])
                if val is not None:
                    return val
    return None


def amd_gpus(base: str = PCI) -> list[str]:
    """PCI sysfs directories of AMD display GPUs that expose amdgpu telemetry."""
    found: list[tuple[int, int, str]] = []
    for dev in sorted(glob.glob(f"{base}/*")):
        if sysfs.read_text(f"{dev}/vendor") != AMD_VENDOR:
            continue
        if not (sysfs.read_text(f"{dev}/class") or "").startswith("0x03"):
            continue
        has_busy = os.path.exists(f"{dev}/gpu_busy_percent")
        has_hwmon = bool(glob.glob(f"{dev}/hwmon/hwmon*"))
        if not (has_busy or has_hwmon):
            continue
        # Prefer discrete Radeon cards (larger VRAM, non-boot iGPU) over small iGPUs.
        vram = _int(sysfs.read_text(f"{dev}/mem_info_vram_total")) or 0
        is_boot = 1 if sysfs.read_text(f"{dev}/boot_vga") == "1" else 0
        found.append((is_boot, -vram, dev))
    found.sort()
    return [dev for _, _, dev in found]


def read_gpu(dev: str) -> dict | None:
    """Read telemetry dict matching GpuNvidia's shape for one AMD GPU sysfs folder."""
    runtime = sysfs.read_text(f"{dev}/power/runtime_status")
    control = sysfs.read_text(f"{dev}/power/control")
    asleep = runtime == "suspended"

    product = sysfs.read_text(f"{dev}/product_name") or ""
    dev_id = (sysfs.read_text(f"{dev}/device") or "").lower()
    name = product.strip() or (f"AMD Radeon ({dev_id})" if dev_id else "AMD Radeon GPU")

    sleep = {"runtime": runtime, "control": control, "asleep": asleep, "users": []}
    if asleep:
        return {"name": name, "vendor": "amd", "asleep": True, "sleep": sleep}

    util = _int(sysfs.read_text(f"{dev}/gpu_busy_percent"))
    vram_used = _int(sysfs.read_text(f"{dev}/mem_info_vram_used"))
    vram_total = _int(sysfs.read_text(f"{dev}/mem_info_vram_total"))
    mem_used_mb = round(vram_used / (1024 * 1024)) if vram_used is not None else None
    mem_total_mb = round(vram_total / (1024 * 1024)) if vram_total is not None else None

    temp_c: int | float | None = None
    power_w: float | None = None
    clock_mhz: int | None = None

    hwmons = sorted(glob.glob(f"{dev}/hwmon/hwmon*"))
    if hwmons:
        hm = hwmons[0]
        raw_t = _int(sysfs.read_text(f"{hm}/temp1_input")) or _int(sysfs.read_text(f"{hm}/temp2_input"))
        if raw_t is not None and raw_t > 0:
            temp_c = round(raw_t / 1000)
        raw_p = _int(sysfs.read_text(f"{hm}/power1_average")) or _int(sysfs.read_text(f"{hm}/power1_input"))
        if raw_p is not None and raw_p >= 0:
            power_w = round(raw_p / 1_000_000, 1)
        raw_f = _int(sysfs.read_text(f"{hm}/freq1_input"))
        if raw_f is not None and raw_f > 0:
            clock_mhz = round(raw_f / 1_000_000)

    if clock_mhz is None:
        clock_mhz = _parse_active_sclk_mhz(sysfs.read_text(f"{dev}/pp_dpm_sclk"))

    return {
        "name": name,
        "vendor": "amd",
        "asleep": False,
        "sleep": sleep,
        "temp_c": temp_c,
        "power_w": power_w,
        "mem_used_mb": mem_used_mb,
        "mem_total_mb": mem_total_mb,
        "util_pct": util,
        "clock_mhz": clock_mhz,
    }


def summary(base: str = PCI) -> dict | None:
    """Telemetry for the primary AMD GPU, or None when no amdgpu device exists."""
    gpus = amd_gpus(base)
    if not gpus:
        return None
    return read_gpu(gpus[0])
