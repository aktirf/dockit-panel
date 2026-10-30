"""Device database: one small TOML file per device (see devices/README.md)."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DeviceEntry:
    name: str
    kind: str                      # laptop, mouse, headset, camera, keyboard, ...
    usb_id: str = ""               # "vendor:product", lower case
    dmi_product: str = ""          # for laptops: the model name from BIOS
    features: list[str] = field(default_factory=list)
    status: str = "untested"       # untested / detected / partial / full
    notes: str = ""
    source: str = ""               # file it was loaded from (not shown to users)


def search_dirs() -> list[Path]:
    dirs = []
    custom = os.environ.get("DOCKIT_DEVICES")
    if custom:
        dirs.append(Path(custom))
    # <repo>/devices when running from the source tree
    dirs.append(Path(__file__).resolve().parents[3] / "devices")
    dirs.append(Path("/usr/share/dockit/devices"))
    return dirs


def load_database(dirs: list[Path] | None = None) -> list[DeviceEntry]:
    entries: list[DeviceEntry] = []
    seen: set[tuple[str, str, str]] = set()
    for directory in dirs if dirs is not None else search_dirs():
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.toml")):
            try:
                data = tomllib.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue  # a broken file must not break the app
            name = str(data.get("name", "")).strip()
            if not name:
                continue
            features = data.get("features", [])
            entry = DeviceEntry(
                name=name,
                kind=str(data.get("kind", "unknown")),
                usb_id=str(data.get("usb_id", "")).strip().lower(),
                dmi_product=str(data.get("dmi_product", "")).strip(),
                features=[str(f) for f in features] if isinstance(features, list) else [],
                status=str(data.get("status", "untested")),
                notes=str(data.get("notes", "")),
                source=str(path),
            )
            key = (entry.usb_id, entry.dmi_product.lower(), entry.name.lower())
            if key in seen:
                continue
            seen.add(key)
            entries.append(entry)
    return entries


def find_by_usb(entries: list[DeviceEntry], usb_id: str) -> DeviceEntry | None:
    wanted = usb_id.strip().lower()
    for entry in entries:
        if entry.usb_id and entry.usb_id == wanted:
            return entry
    return None


def find_laptop(entries: list[DeviceEntry], product: str) -> DeviceEntry | None:
    wanted = " ".join(product.split()).lower()
    for entry in entries:
        if entry.dmi_product and " ".join(entry.dmi_product.split()).lower() == wanted:
            return entry
    return None
