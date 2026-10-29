"""Small safe helpers for reading files in /sys."""

from __future__ import annotations

import os
from pathlib import Path


def read_text(path: str | Path) -> str | None:
    """Read a small text file. Return None if it is missing or unreadable."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, ValueError):
        return None


def exists(path: str | Path) -> bool:
    return Path(path).exists()


def is_writable(path: str | Path) -> bool:
    return os.access(path, os.W_OK)
