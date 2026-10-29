"""Statuses a feature can have on this laptop."""

from enum import Enum


class Status(str, Enum):
    OK = "ok"                    # works, current value can be shown
    NEEDS_SETUP = "needs_setup"  # can be fixed (permissions, missing package, service)
    NEEDS_ROOT = "needs_root"    # works, but needs root or a reboot to change
    UNAVAILABLE = "unavailable"  # hardware or kernel does not support it


LABELS_RU = {
    Status.OK: "Работает",
    Status.NEEDS_SETUP: "Нужна настройка",
    Status.NEEDS_ROOT: "Нужен root или перезагрузка",
    Status.UNAVAILABLE: "Недоступно",
}
