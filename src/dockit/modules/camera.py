"""Built-in camera: found? switched on or off? (read only; switching is done by the service)."""

from __future__ import annotations

from ..core.module import Detection, Module
from ..core.status import Status
from ..daemon.actions import camera_state
from ..daemon.client import daemon_running


class Camera(Module):
    id = "camera"
    name = "Веб-камера (включение и выключение)"
    source = "usb authorized"

    def detect(self) -> Detection:
        cameras = camera_state()["cameras"]
        if not cameras:
            return Detection(
                Status.UNAVAILABLE,
                "Камера не найдена среди известных устройств (база devices/).",
            )
        if not daemon_running():
            return Detection(
                Status.NEEDS_SETUP,
                "Камера найдена, но для переключения нужна служба DOCKIT.",
            )
        return Detection(Status.OK, "Камеру можно включать и выключать.")

    def get_state(self):
        cameras = camera_state()["cameras"]
        return {"enabled": all(c["enabled"] for c in cameras)} if cameras else None

    def fix_hint(self) -> str:
        return "Установите и запустите службу DOCKIT: sudo scripts/install-dev.sh."
