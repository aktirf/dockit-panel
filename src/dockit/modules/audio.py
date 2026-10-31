"""Sound devices (PipeWire / PulseAudio), read only here."""

from __future__ import annotations

from ..core import audio
from ..core.module import Detection, Module
from ..core.status import Status


class Audio(Module):
    id = "audio"
    name = "Звук"
    source = "pactl"

    def detect(self) -> Detection:
        try:
            devices = audio.list_devices()
        except audio.AudioError as exc:
            return Detection(Status.UNAVAILABLE, str(exc))
        outputs = [d for d in devices if d.kind == "output"]
        inputs = [d for d in devices if d.kind == "input"]
        if not outputs:
            return Detection(Status.UNAVAILABLE, "Устройства вывода звука не найдены.")
        current = next((d.description for d in outputs if d.default), outputs[0].description)
        return Detection(Status.OK, f"Выводов: {len(outputs)}, микрофонов: {len(inputs)}. Сейчас звук идёт на: {current}.")

    def fix_hint(self) -> str:
        return "Установите PipeWire и libpulse: sudo pacman -S pipewire pipewire-pulse libpulse"
