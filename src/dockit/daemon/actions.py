"""The only things the root service is allowed to change.

Every action checks its input strictly. The client never sends a file path:
the service decides which files to touch.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ..core import display, kbd_backlight, sysfs, tuning
from ..core.usb import BASE as USB_BASE
from ..core.usb import list_usb
from ..peripherals.database import DeviceEntry, load_database

PROFILE = "/sys/firmware/acpi/platform_profile"
CHOICES = "/sys/firmware/acpi/platform_profile_choices"

_PPD_MAP = {
    "low-power": "power-saver",
    "balanced": "balanced",
    "performance": "performance",
}

# kernel names of USB ports look like "3-1" or "1-2.4"
PORT_RE = re.compile(r"^[0-9]+-[0-9]+(\.[0-9]+)*$")


class ActionError(Exception):
    """A request was refused. The message is safe to show to the user."""


def _sync_power_state(value: str, cpu_base: str = tuning.CPU, use_ppd: bool = True) -> None:
    """Keep power-profiles-daemon (serpantinum/KDE/GNOME) and amd-pstate-epp governor in sync."""
    if use_ppd:
        ppd = shutil.which("powerprofilesctl")
        ppd_name = _PPD_MAP.get(value)
        if ppd and ppd_name:
            try:
                proc = subprocess.run([ppd, "set", ppd_name], capture_output=True, text=True, timeout=3)
                if proc.returncode == 0:
                    return
            except (OSError, subprocess.TimeoutExpired):
                pass

    # Fallback when power-profiles-daemon is absent: unlock EPP on amd-pstate-epp / intel_pstate
    driver = sysfs.read_text(f"{cpu_base}/cpu0/cpufreq/scaling_driver") or ""
    avail = (sysfs.read_text(f"{cpu_base}/cpu0/cpufreq/scaling_available_governors") or "").split()
    if driver not in ("amd-pstate-epp", "intel_pstate") or "powersave" not in avail:
        return
    gov = "performance" if value == "performance" and "performance" in avail else "powersave"
    for path in sorted(Path(cpu_base).glob("cpu[0-9]*/cpufreq/scaling_governor")):
        try:
            path.write_text(gov, encoding="ascii")
        except OSError:
            pass
    # If leaving dynamic EPP without power-profiles-daemon, restore a matching manual EPP.
    if gov == "powersave" and tuning.read_epp(cpu_base) == "dynamic":
        choices = tuning.epp_choices(cpu_base)
        target_epp = "power" if value == "low-power" else "balance_performance"
        if target_epp not in choices:
            target_epp = "default" if "default" in choices else ""
        if target_epp:
            for f in tuning.epp_files(cpu_base):
                try:
                    Path(f).write_text(target_epp, encoding="ascii")
                except OSError:
                    pass


def set_power_profile(
    value,
    profile_path: str = PROFILE,
    choices_path: str = CHOICES,
    cpu_base: str = tuning.CPU,
) -> dict:
    if not isinstance(value, str):
        raise ActionError("Режим должен быть строкой.")
    choices = (sysfs.read_text(choices_path) or "").split()
    if not choices:
        raise ActionError("Эта модель не поддерживает смену режима мощности.")
    if value == "dynamic":
        if "balanced" not in choices or not tuning.has_dynamic_epp(cpu_base):
            raise ActionError("Динамический режим CPU не поддерживается этим ядром или процессором.")
        if profile_path == PROFILE:
            _sync_power_state("balanced", cpu_base=cpu_base)
        if sysfs.read_text(profile_path) != "balanced":
            try:
                Path(profile_path).write_text("balanced", encoding="ascii")
            except OSError as exc:
                raise ActionError(f"Не удалось записать режим: {exc.strerror or 'ошибка'}.") from exc
        # Ensure powersave governor so EPP accepts "dynamic" on amd-pstate-epp.
        _sync_power_state("balanced", cpu_base=cpu_base, use_ppd=False)
        try:
            for f in tuning.epp_files(cpu_base):
                Path(f).write_text("dynamic", encoding="ascii")
        except OSError as exc:
            raise ActionError(f"Не удалось включить динамический режим: {exc.strerror or 'ошибка'}.") from exc
        return {"profile": sysfs.read_text(profile_path), "epp": tuning.read_epp(cpu_base)}
    if value not in choices:
        raise ActionError(f"Недопустимый режим. Доступно: {', '.join(choices)}.")
    if profile_path == PROFILE:
        _sync_power_state(value, cpu_base=cpu_base)
    if sysfs.read_text(profile_path) != value:
        try:
            Path(profile_path).write_text(value, encoding="ascii")
        except OSError as exc:
            raise ActionError(f"Не удалось записать режим: {exc.strerror or 'ошибка'}.") from exc
    return {"profile": sysfs.read_text(profile_path)}


def _camera_devices(usb_base: str, entries: list[DeviceEntry] | None):
    """Connected USB devices that the database says are cameras."""
    if entries is None:
        entries = load_database()
    camera_ids = set()
    for entry in entries:
        if entry.kind == "camera":
            camera_ids.update(i for i in [entry.usb_id, *entry.usb_ids] if i)
    return [d for d in list_usb(usb_base) if d.usb_id in camera_ids]


def camera_state(usb_base: str = USB_BASE, entries: list[DeviceEntry] | None = None) -> dict:
    cameras = []
    for dev in _camera_devices(usb_base, entries):
        raw = sysfs.read_text(Path(usb_base) / dev.port / "authorized")
        cameras.append({"usb_id": dev.usb_id, "port": dev.port, "enabled": raw == "1"})
    return {"cameras": cameras}


def set_camera(enabled, usb_base: str = USB_BASE, entries: list[DeviceEntry] | None = None) -> dict:
    if not isinstance(enabled, bool):
        raise ActionError("Значение должно быть true или false.")
    devices = _camera_devices(usb_base, entries)
    if not devices:
        raise ActionError("Камера не найдена в базе устройств.")
    for dev in devices:
        if not PORT_RE.match(dev.port):
            raise ActionError("Неожиданное имя USB-порта.")
        try:
            (Path(usb_base) / dev.port / "authorized").write_text(
                "1" if enabled else "0", encoding="ascii"
            )
        except OSError as exc:
            raise ActionError(f"Не удалось переключить камеру: {exc.strerror or 'ошибка'}.") from exc
    return camera_state(usb_base, entries)


def set_brightness(value, base: str = display.BACKLIGHT) -> dict:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100:
        raise ActionError("Яркость должна быть числом от 1 до 100.")
    dev = display.backlight_device(base)
    if dev is None:
        raise ActionError("Управление яркостью экрана не найдено.")
    top = int(sysfs.read_text(f"{dev}/max_brightness") or 0)
    if top <= 0:
        raise ActionError("Не удалось узнать максимальную яркость.")
    target = max(1, round(top * value / 100))
    try:
        Path(f"{dev}/brightness").write_text(str(target), encoding="ascii")
    except OSError as exc:
        raise ActionError(f"Не удалось изменить яркость: {exc.strerror or 'ошибка'}.") from exc
    return {"brightness": display.brightness_percent(base)}


def set_boost(value, base: str = tuning.CPU) -> dict:
    if not isinstance(value, bool):
        raise ActionError("Значение должно быть true или false.")
    if tuning.read_boost(base) is None:
        raise ActionError("Эта модель не поддерживает отключение Turbo Boost.")
    try:
        Path(tuning.boost_path(base)).write_text("1" if value else "0", encoding="ascii")
    except OSError as exc:
        raise ActionError(f"Не удалось изменить Turbo Boost: {exc.strerror or 'ошибка'}.") from exc
    return {"boost": tuning.read_boost(base)}


def set_epp(value, base: str = tuning.CPU) -> dict:
    choices = tuning.epp_choices(base)
    if not isinstance(value, str) or value not in choices:
        raise ActionError(f"Недопустимое значение. Доступно: {', '.join(choices) or 'нет'}.")
    try:
        for f in tuning.epp_files(base):
            Path(f).write_text(value, encoding="ascii")
    except OSError as exc:
        raise ActionError(f"Не удалось изменить: {exc.strerror or 'ошибка'}.") from exc
    return {"epp": tuning.read_epp(base)}


def set_gpu_power_limit(value) -> dict:
    import subprocess
    if isinstance(value, bool) or not isinstance(value, int):
        raise ActionError("Лимит должен быть числом (ватты).")
    limits = tuning.gpu_power_limits()
    if limits is None:
        raise ActionError("Видеокарта не позволяет менять лимит мощности.")
    if not limits["min"] <= value <= limits["max"]:
        raise ActionError(f"Допустимо от {limits['min']} до {limits['max']} Вт.")
    try:
        proc = subprocess.run(["nvidia-smi", "-pl", str(value)], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ActionError("Не удалось запустить nvidia-smi.") from exc
    if proc.returncode != 0:
        raise ActionError("Драйвер отказался менять лимит мощности.")
    return {"limit": value}


def set_kbd_backlight(
    value,
    hid_base: str = kbd_backlight.HID_BASE,
    leds_base: str = kbd_backlight.LEDS_BASE,
    dev_base: str = kbd_backlight.DEV_BASE,
    ioctl_fn=kbd_backlight._ioctl_feature,
) -> dict:
    if not isinstance(value, dict):
        raise ActionError("Параметры подсветки должны быть объектом.")
    autonomous = value.get("autonomous", False)
    if not isinstance(autonomous, bool):
        raise ActionError("Поле autonomous должно быть true или false.")
    on = value.get("on", True)
    if not isinstance(on, bool):
        raise ActionError("Поле on должно быть true или false.")
    brightness = value.get("brightness", 100)
    if isinstance(brightness, bool) or not isinstance(brightness, int) or not 0 <= brightness <= 100:
        raise ActionError("Яркость подсветки должна быть числом от 0 до 100.")
    raw_color = value.get("color", "#5AB0FF")
    try:
        color = kbd_backlight.normalize_hex_color(raw_color)
    except ValueError as exc:
        raise ActionError("Цвет должен быть в формате #RRGGBB.") from exc

    lamparrays = kbd_backlight.discover_lamparray(hid_base)
    if lamparrays:
        applied = []
        for dev in lamparrays:
            try:
                applied.append(
                    kbd_backlight.apply_lamparray(
                        dev,
                        on=on,
                        brightness=brightness,
                        color=color,
                        autonomous=autonomous,
                        dev_base=dev_base,
                        ioctl_fn=ioctl_fn,
                    )
                )
            except (OSError, ValueError) as exc:
                msg = getattr(exc, "strerror", None) or "ошибка"
                raise ActionError(f"Не удалось изменить подсветку: {msg}.") from exc
        return applied[0]

    leds = kbd_backlight.discover_leds(leds_base)
    if leds:
        applied = []
        for led in leds:
            try:
                applied.append(
                    kbd_backlight.apply_led(led, on=on, brightness=brightness, leds_base=leds_base)
                )
            except (OSError, ValueError) as exc:
                msg = getattr(exc, "strerror", None) or "ошибка"
                raise ActionError(f"Не удалось изменить подсветку: {msg}.") from exc
        return applied[0]

    raise ActionError("Подсветка клавиатуры не найдена.")
