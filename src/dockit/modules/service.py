"""Is the DOCKIT background service running? Needed for every action that changes something."""

from __future__ import annotations

from ..core.module import Detection, Module
from ..core.status import Status
from ..daemon.client import daemon_running


class Service(Module):
    id = "service"
    name = "Фоновая служба DOCKIT"
    source = "dockit.service"

    def detect(self) -> Detection:
        if daemon_running():
            return Detection(Status.OK, "Служба запущена, изменения настроек доступны.")
        return Detection(
            Status.NEEDS_SETUP,
            "Служба не запущена: настройки можно смотреть, но не менять.",
        )

    def fix_hint(self) -> str:
        return "Установите службу: sudo scripts/install-dev.sh (из папки проекта)."
