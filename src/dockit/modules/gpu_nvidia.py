"""NVIDIA graphics card: temperature, power, memory, load (read only, via nvidia-smi)."""

from __future__ import annotations

import glob
import shutil
import subprocess

from ..core import sysfs
from ..core.module import Detection, Module
from ..core.status import Status

FIELDS = [
    ("name", "name"),
    ("temp_c", "temperature.gpu"),
    ("power_w", "power.draw"),
    ("power_limit_w", "power.limit"),
    ("mem_used_mb", "memory.used"),
    ("mem_total_mb", "memory.total"),
    ("util_pct", "utilization.gpu"),
    ("clock_mhz", "clocks.gr"),
]
QUERY = ",".join(q for _, q in FIELDS)

NVIDIA_VENDOR = "0x10de"


def _number(text: str):
    """'42' -> 42, '7.12' -> 7.12, '[N/A]' -> None."""
    try:
        value = float(text)
    except ValueError:
        return None
    return int(value) if value.is_integer() else value


def parse_smi_csv(text: str) -> list[dict]:
    """Parse the CSV that nvidia-smi prints with --format=csv,noheader,nounits."""
    gpus = []
    n = len(FIELDS)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < n:
            continue
        # A card name may contain a comma: glue the extra pieces back together.
        extra = len(parts) - n
        name = ", ".join(parts[: extra + 1])
        values = parts[extra + 1 :]
        gpu = {"name": name}
        for (key, _), raw in zip(FIELDS[1:], values):
            gpu[key] = _number(raw)
        gpus.append(gpu)
    return gpus


def nvidia_card_present() -> bool:
    """True if a PCI display device made by NVIDIA exists (even without a driver)."""
    for dev in glob.glob("/sys/bus/pci/devices/*"):
        if sysfs.read_text(f"{dev}/vendor") == NVIDIA_VENDOR:
            if (sysfs.read_text(f"{dev}/class") or "").startswith("0x03"):
                return True
    return False


def _query() -> tuple[list[dict] | None, str]:
    """Return (gpus, error). Never raises."""
    tool = shutil.which("nvidia-smi")
    if tool is None:
        return None, "missing"
    try:
        proc = subprocess.run(
            [tool, f"--query-gpu={QUERY}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, "failed"
    if proc.returncode != 0:
        return None, "failed"
    gpus = parse_smi_csv(proc.stdout)
    return (gpus, "") if gpus else (None, "failed")


def thermal_throttled() -> bool | None:
    """True if the card lowers its speed because of heat; None if the driver does not say."""
    tool = shutil.which("nvidia-smi")
    if tool is None:
        return None
    for prefix in ("clocks_event_reasons", "clocks_throttle_reasons"):   # new and old driver names
        fields = f"{prefix}.hw_thermal_slowdown,{prefix}.sw_thermal_slowdown"
        try:
            proc = subprocess.run([tool, f"--query-gpu={fields}", "--format=csv,noheader,nounits"],
                                  capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode == 0 and proc.stdout.strip():
            tokens = [t.strip() for t in proc.stdout.replace("\n", ",").split(",")]
            return "Active" in tokens
    return None


class GpuNvidia(Module):
    id = "gpu_nvidia"
    name = "Видеокарта NVIDIA"
    source = "nvidia-smi"

    def detect(self) -> Detection:
        gpus, error = _query()
        if gpus:
            return Detection(Status.OK, f"{gpus[0]['name']}: данные доступны.")
        if error == "missing":
            if nvidia_card_present():
                return Detection(
                    Status.NEEDS_SETUP,
                    "Видеокарта NVIDIA есть, но утилита nvidia-smi не найдена.",
                )
            return Detection(Status.UNAVAILABLE, "Видеокарта NVIDIA не найдена.")
        return Detection(
            Status.NEEDS_SETUP,
            "Утилита nvidia-smi не смогла получить данные: драйвер не загружен.",
        )

    def get_state(self):
        gpus, _ = _query()
        if not gpus:
            return None
        gpu = gpus[0]
        if (gpu.get("temp_c") or 0) >= 75:       # only worth asking when the card is hot
            gpu["throttled"] = thermal_throttled()
        return gpu

    def fix_hint(self) -> str:
        if nvidia_card_present():
            return (
                "Установите драйвер NVIDIA (на EndeavourOS: пакеты nvidia-open и "
                "nvidia-utils) и перезагрузитесь."
            )
        return ""
