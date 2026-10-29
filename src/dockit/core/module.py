"""Base class for every feature (module) of DOCKIT.

One feature = one file in dockit/modules/. A module answers three questions:
  detect()    - is this feature available on this laptop, and in what state?
  get_state() - what is the current value?
  fix_hint()  - if it does not work, what can the user do?

Modules must only READ in detect() and get_state(). Changing anything on the
system happens elsewhere and only after the user confirms.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .status import Status


@dataclass
class Detection:
    status: Status
    detail: str = ""  # short explanation shown to the user


class Module(ABC):
    id: str = ""    # short stable name, e.g. "power_profile"
    name: str = ""  # human-readable name, e.g. "Режим производительности"
    source: str = ""  # where the data comes from, e.g. "platform_profile"

    @abstractmethod
    def detect(self) -> Detection:
        """Check availability. Must be safe: read-only, never raise."""

    def get_state(self) -> Any:
        """Return the current value, or None if not available."""
        return None

    def fix_hint(self) -> str:
        """Tell the user how to fix the problem. Empty if nothing to fix."""
        return ""
