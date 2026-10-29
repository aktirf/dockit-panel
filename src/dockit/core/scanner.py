"""First-run scan: which features exist on this laptop and in what state.

The scan only READS. It never changes anything on the system.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from typing import Any

from .module import Module
from .status import LABELS_RU, Status
from . import sysfs

DMI = "/sys/class/dmi/id"


@dataclass
class ScanItem:
    id: str
    name: str
    source: str
    status: Status
    detail: str
    state: Any = None
    hint: str = ""


@dataclass
class ScanResult:
    system: dict[str, str] = field(default_factory=dict)
    items: list[ScanItem] = field(default_factory=list)

    def counts(self) -> dict[Status, int]:
        return {s: sum(1 for i in self.items if i.status is s) for s in Status}


def system_info() -> dict[str, str]:
    """Model and OS info. No serial numbers, no hostname, no user names."""
    info = {
        "vendor": sysfs.read_text(f"{DMI}/sys_vendor") or "unknown",
        "model": sysfs.read_text(f"{DMI}/product_name") or "unknown",
        "bios": sysfs.read_text(f"{DMI}/bios_version") or "unknown",
        "kernel": platform.release(),
        "distro": _distro(),
    }
    return info


def _distro() -> str:
    text = sysfs.read_text("/etc/os-release") or ""
    for line in text.splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip('"')
    return "unknown"


def scan(modules: list[type[Module]] | None = None) -> ScanResult:
    if modules is None:
        from ..modules import ALL_MODULES

        modules = ALL_MODULES

    result = ScanResult(system=system_info())
    for cls in modules:
        mod = cls()
        try:
            det = mod.detect()
            state = mod.get_state() if det.status is not Status.UNAVAILABLE else None
            hint = mod.fix_hint() if det.status is not Status.OK else ""
            item = ScanItem(mod.id, mod.name, mod.source, det.status, det.detail, state, hint)
        except Exception as exc:  # a broken module must never break the whole scan
            item = ScanItem(
                mod.id, mod.name, mod.source, Status.UNAVAILABLE,
                f"Ошибка проверки: {type(exc).__name__}",
            )
        result.items.append(item)
    return result


def format_report(result: ScanResult) -> str:
    """Plain text report the user can paste into a GitHub issue."""
    lines = ["DOCKIT report", ""]
    for key, value in result.system.items():
        lines.append(f"{key}: {value}")
    lines.append("")
    for item in result.items:
        lines.append(f"[{LABELS_RU[item.status]}] {item.name} ({item.source})")
        lines.append(f"    {item.detail}")
        if item.hint:
            lines.append(f"    Как исправить: {item.hint}")
    counts = result.counts()
    lines.append("")
    lines.append(
        "Итого: "
        + ", ".join(f"{LABELS_RU[s]}: {counts[s]}" for s in Status)
    )
    return "\n".join(lines)
