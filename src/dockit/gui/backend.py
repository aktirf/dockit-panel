"""Qt side: runs scans in a worker thread and passes actions to the service.

The window never blocks: every slow thing (scan, polkit password dialog)
runs in a thread and reports back through signals.
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import threading
import time
from collections import deque

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from ..core import audio, processes, profiles, sysfs
from ..core import idle
from ..core.cpu import CpuMonitor
from ..core.scanner import scan
from ..daemon import client
from ..daemon.actions import PROFILE
from ..modules.battery import ac_online
from . import viewmodel

MODE_NAMES = {m["id"]: m["name"] for m in viewmodel.MODES}


class Backend(QObject):
    stateChanged = Signal()
    toastChanged = Signal()
    settingsChanged = Signal()
    trayChanged = Signal()
    _snapshot = Signal(object)   # worker thread -> main thread
    _finished = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._state = viewmodel.empty()
        self._toast = ""
        self._cpu = CpuMonitor()
        self._cpu_name = self._cpu.name()
        self._cpu_hist: deque = deque(maxlen=100)
        self._gpu_hist: deque = deque(maxlen=100)
        self._ssd_hist: deque = deque(maxlen=100)
        self._max_temp: dict[str, float] = {}
        self._journal: deque = deque(maxlen=30)
        self._warn_at = 0.0
        self._tray_available = False
        self._scenario = profiles.load_scenario()
        self._idle = idle.IdleWatcher()
        self._auto_last: str | None = None
        self._busy = False
        self._hist_at = 0.0
        self._snapshot.connect(self._apply)
        self._finished.connect(self._done)
        self._timer = QTimer(self)
        self._settings = self._load_settings()
        self._timer.setInterval(self._settings["interval"] * 1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    # ---- what the window reads ----
    @Property("QVariantMap", notify=stateChanged)
    def state(self):
        return self._state

    @Property(str, notify=toastChanged)
    def toast(self):
        return self._toast

    def _say(self, text: str) -> None:
        self._toast = text
        self.toastChanged.emit()

    @Slot(str)
    def say(self, text: str) -> None:
        self._say(text)

    @Slot()
    def clearToast(self) -> None:
        if self._toast:
            self._toast = ""
            self.toastChanged.emit()

    # ---- settings (saved in ~/.config/dockit/settings.json) ----
    DEFAULTS = {"interval": 3, "warn_temp": 90, "notify": True, "tray": False}

    @staticmethod
    def _settings_path() -> str:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return os.path.join(base, "dockit", "settings.json")

    @staticmethod
    def _autostart_path() -> str:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return os.path.join(base, "autostart", "dockit.desktop")

    def _load_settings(self) -> dict:
        data = dict(self.DEFAULTS)
        try:
            with open(self._settings_path(), encoding="utf-8") as f:
                loaded = json.load(f)
            if loaded.get("interval") in (1, 3, 5, 10):
                data["interval"] = loaded["interval"]
            if loaded.get("warn_temp") in (0, 80, 85, 90, 95):
                data["warn_temp"] = loaded["warn_temp"]
            for key in ("notify", "tray"):
                if isinstance(loaded.get(key), bool):
                    data[key] = loaded[key]
        except (OSError, ValueError, AttributeError):
            pass
        return data

    def _save_settings(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._settings_path()), exist_ok=True)
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(self._settings, f)
        except OSError:
            self._say("Не удалось сохранить настройку")
        self.settingsChanged.emit()

    def _settings_view(self) -> dict:
        view = dict(self._settings)
        view["autostart"] = os.path.exists(self._autostart_path())
        view["trayAvailable"] = self._tray_available
        view["notifyAvailable"] = shutil.which("notify-send") is not None
        return view

    @Property(int, notify=settingsChanged)
    def interval(self) -> int:
        return self._settings["interval"]

    @Property(bool, notify=trayChanged)
    def trayActive(self) -> bool:
        return self._tray_available and self._settings["tray"]

    @Property(str, constant=True)
    def version(self) -> str:
        from .. import __version__
        return __version__

    def set_tray_available(self, value: bool) -> None:
        self._tray_available = value
        self.trayChanged.emit()

    @Slot(int)
    def setInterval(self, seconds: int) -> None:
        if seconds not in (1, 3, 5, 10):
            return
        self._settings["interval"] = seconds
        self._timer.setInterval(seconds * 1000)
        self._save_settings()
        self.refresh()

    @Slot(int)
    def setWarnTemp(self, value: int) -> None:
        if value in (0, 80, 85, 90, 95):
            self._settings["warn_temp"] = value
            self._save_settings()
            self.refresh()

    @Slot(bool)
    def setNotify(self, value: bool) -> None:
        self._settings["notify"] = bool(value)
        self._save_settings()
        self.refresh()

    @Slot(bool)
    def setTray(self, value: bool) -> None:
        self._settings["tray"] = bool(value)
        self._save_settings()
        self.trayChanged.emit()
        self.refresh()

    @Slot(bool)
    def setAutostart(self, value: bool) -> None:
        path = self._autostart_path()
        try:
            if value:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write("[Desktop Entry]\nType=Application\nName=DOCKIT\nExec=dockit gui\n"
                            "Icon=dockit\nX-GNOME-Autostart-enabled=true\n")
                self._say("Автозапуск включён. Если окно не появится при входе, добавьте в конфиг niri: "
                          "spawn-at-startup \"dockit\" \"gui\"")
            elif os.path.exists(path):
                os.remove(path)
                self._say("Автозапуск выключен")
        except OSError:
            self._say("Не удалось изменить автозапуск")
        self.settingsChanged.emit()
        self.refresh()

    # ---- notifications, journal, cooling ----
    def _log(self, text: str) -> None:
        self._journal.append({"time": datetime.datetime.now().strftime("%H:%M"), "text": text})

    def _notify(self, title: str, body: str) -> None:
        if not self._settings["notify"] or shutil.which("notify-send") is None:
            return
        try:
            subprocess.Popen(["notify-send", "-a", "DOCKIT", "-i", "dockit", title, body],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass

    def _cooling(self, cpu: dict, cpu_temp, gpu_temp, ssd_temp, gpu_throttled: bool) -> dict:
        warn = self._settings["warn_temp"]
        max_mhz = self._cpu.max_frequency_mhz()
        freq = cpu.get("freq_mhz")
        load = cpu.get("load_pct") or 0
        cpu_throttled = bool(cpu_temp is not None and (
            cpu_temp >= 95 or (cpu_temp >= 85 and load >= 80 and max_mhz and freq and freq < 0.7 * max_mhz)))
        hottest = max([t for t in (cpu_temp, gpu_temp) if t is not None], default=None)
        hot = bool(warn and hottest is not None and hottest >= warn)
        now = time.monotonic()
        if hot and now - self._warn_at > 300:
            self._warn_at = now
            self._log(f"Перегрев: {hottest:.0f} °C")
            self._notify("DOCKIT: ноутбук горячий", f"Температура {hottest:.0f} °C. Можно переключить режим на «Баланс» или «Тишина».")

        def part(key, now_value, hist, throttled=False):
            return {"has": now_value is not None,
                    "now": f"{now_value:.0f}" if now_value is not None else "—",
                    "max": f"{self._max_temp[key]:.0f}" if key in self._max_temp else "—",
                    "values": list(hist), "throttled": throttled}

        return {"cpu": part("cpu", cpu_temp, self._cpu_hist, cpu_throttled),
                "gpu": part("gpu", gpu_temp, self._gpu_hist, gpu_throttled),
                "ssd": part("ssd", ssd_temp, self._ssd_hist),
                "warn": warn, "hot": hot}

    @Slot()
    def copyReport(self) -> None:
        from PySide6.QtGui import QGuiApplication
        st = self._state
        lines = [f"DOCKIT {self.version}", ", ".join(f"{k}: {v}" for k, v in st.get("system", {}).items()), ""]
        for f in st.get("features", []):
            lines.append(f"[{f['statusText']}] {f['name']}: {f['detail']}")
            if f.get("hint"):
                lines.append(f"    Как исправить: {f['hint']}")
        QGuiApplication.clipboard().setText("\n".join(lines))
        self._say("Отчёт скопирован. Его можно вставить в сообщение об ошибке.")

    @Slot()
    def shutdown(self) -> None:
        self._idle.stop()

    @Slot(str, result=str)
    def describeProgram(self, name: str) -> str:
        return processes.describe(name)

    @Slot(str, result=str)
    def describeToggle(self, what: str) -> str:
        return {
            "camera": "Включает и выключает веб-камеру на уровне системы.",
            "mic": "Отключает звук микрофона по умолчанию.",
            "wifi": "Включает и выключает Wi-Fi.",
            "bluetooth": "Включает и выключает Bluetooth.",
        }.get(what, "")

    # ---- scanning ----
    @Slot()
    def refresh(self) -> None:
        if self._busy:
            return
        self._busy = True
        threading.Thread(target=self._collect, daemon=True).start()

    def _collect(self) -> None:
        try:
            result = scan()
            mode = sysfs.read_text(PROFILE)
            cpu = self._cpu.sample()
            sensors = next((i for i in result.items if i.id == "sensors"), None)
            temp = viewmodel.cpu_temperature(sensors.state if sensors else None)
            now = time.monotonic()
            fresh = now - self._hist_at >= 2.5
            if fresh:
                self._hist_at = now
            if temp is not None and fresh:
                self._cpu_hist.append(temp)
            gpu_item = next((i for i in result.items if i.id == "gpu_nvidia"), None)
            gpu_temp = gpu_item.state.get("temp_c") if gpu_item and gpu_item.state else None
            if fresh and gpu_temp is not None:
                self._gpu_hist.append(gpu_temp)
            ssd_temp = viewmodel.chip_temps(sensors.state if sensors else None).get("SSD (NVMe)")
            if fresh and ssd_temp is not None:
                self._ssd_hist.append(ssd_temp)
            for key, value in (("cpu", temp), ("gpu", gpu_temp), ("ssd", ssd_temp)):
                if value is not None:
                    self._max_temp[key] = max(self._max_temp.get(key, value), value)
            cooling = self._cooling(cpu, temp, gpu_temp, ssd_temp,
                                    bool(gpu_item and gpu_item.state and gpu_item.state.get("throttled")))
            try:
                muted = next((d.muted for d in audio.list_devices() if d.kind == "input" and d.default), None)
            except audio.AudioError:
                muted = None
            available, rules = profiles.load()
            scenarios = [{"id": p.id, "name": p.name} for p in available.values()]
            scenarios.append({"id": "auto", "name": "Авто"})
            note = ""
            if self._scenario == "auto":
                self._idle.set_minutes([r.idle for r in rules if r.idle])
                running = profiles.running_processes()
                matched = profiles.match_rule(rules, running, ac_online(), self._idle.reached(), temp)
                reason = ""
                if matched is not None:
                    wanted = matched.profile
                    reason = profiles.explain(matched, running)
                else:
                    fallback = profiles.load_fallback()
                    wanted = fallback if fallback in available else None
                    reason = "ни одно правило не подошло"
                if wanted and wanted != self._auto_last:
                    first = self._auto_last is None
                    self._auto_last = wanted
                    note = self._apply_profile(available[wanted])
                    self._log(f"Авто: «{available[wanted].name}» ({reason})")
                    if not first:
                        self._notify("DOCKIT", f"Включён профиль «{available[wanted].name}»: {reason}")
            else:
                self._idle.stop()
            state = viewmodel.build(result, mode, cpu, self._cpu_name, self._cpu_hist, self._gpu_hist,
                                    muted, scenarios, self._scenario)
            state["cooling"] = cooling
            state["journal"] = list(reversed(self._journal))[:6]
            state["settings"] = self._settings_view()
            state["profiles"] = viewmodel.profile_cards(available, rules)
            state["apps"] = processes.user_programs()
            state["idleAvailable"] = idle.available()
            fb = profiles.load_fallback()
            state["fallback"] = fb if fb in available else ""
            try:
                devices = audio.list_devices()
            except audio.AudioError:
                devices = []
            state["audio"] = {
                "outputs": [d.description for d in devices if d.kind == "output"],
                "inputs": [d.description for d in devices if d.kind == "input"],
            }
            self._snapshot.emit(state)
            if note:
                self._finished.emit(note)
        except Exception:  # the window must stay alive whatever happens
            self._snapshot.emit(None)

    @Slot(object)
    def _apply(self, state) -> None:
        self._busy = False
        if state is not None:
            self._state = state
            self.stateChanged.emit()

    @Slot(str)
    def _done(self, message: str) -> None:
        if message:
            self._say(message)
        self.refresh()

    # ---- actions (all in threads) ----
    def _run(self, work) -> None:
        def target():
            try:
                message = work()
            except Exception:
                message = "Не удалось выполнить действие."
            self._finished.emit(message)

        threading.Thread(target=target, daemon=True).start()

    def _apply_profile(self, profile: profiles.Profile) -> str:
        errors: list[str] = []

        def ask(payload: dict):
            result, error = client.ask(payload)
            if result is None:
                errors.append(error)
            return result

        profiles.apply(profile, ask)
        if errors:
            return f"Профиль «{profile.name}»: {errors[0]}"
        return f"Профиль «{profile.name}» включён"

    @Slot(str)
    def setMode(self, mode: str) -> None:
        if mode not in profiles.POWER_VALUES:
            return

        def work() -> str:
            result, error = client.ask({"action": "set_power_profile", "value": mode})
            if result is not None:
                self._log(f"Режим мощности: {MODE_NAMES.get(mode, mode)}")
            return f"Режим: {MODE_NAMES.get(mode, mode)}" if result is not None else error

        self._run(work)

    @Slot(str)
    def setScenario(self, scenario: str) -> None:
        self._scenario = scenario
        profiles.save_scenario(scenario)
        self._auto_last = None
        self._state = dict(self._state, scenario=scenario)
        self.stateChanged.emit()
        if scenario == "auto":
            self._say("Автоматический выбор профиля включён")
            self.refresh()
            return
        available, _ = profiles.load()
        profile = available.get(scenario)
        if profile is None:
            return
        self._log(f"Вручную: «{profile.name}»")
        self._run(lambda: self._apply_profile(profile))

    @Slot(str, str, str, str, str)
    def saveProfile(self, pid: str, power: str, camera: str, output: str, mic: str) -> None:
        available, _ = profiles.load()
        if pid not in available:
            return
        try:
            profiles.save_profile(pid, power, camera, output, mic)
        except (ValueError, OSError):
            self._say("Не удалось сохранить профиль")
            return
        self._say(f"Профиль «{available[pid].name}» сохранён. Нажмите «Применить сейчас», чтобы включить его.")
        self.refresh()

    @Slot(str, str, str, int, int, str)
    def saveRule(self, pid: str, programs: str, when: str, idle_minutes: int, temp: int, hours: str) -> None:
        available, _ = profiles.load()
        if pid not in available:
            return
        names = [n for n in programs.split(",") if n.strip()]
        try:
            profiles.save_rule(pid, names, when, idle_minutes, temp=temp, hours=hours)
        except (ValueError, OSError):
            self._say("Не удалось сохранить правило")
            return
        self._auto_last = None
        self._say("Правило сохранено")
        self.refresh()

    @Slot(str)
    def saveFallback(self, value: str) -> None:
        try:
            profiles.save_fallback(value)
        except (ValueError, OSError):
            self._say("Не удалось сохранить")
            return
        self._auto_last = None
        self._say("Сохранено")
        self.refresh()

    @Slot(str)
    def toggle(self, what: str) -> None:
        items = {t["id"]: t for t in self._state.get("toggles", [])}
        item = items.get(what)
        if item is None or not item.get("can"):
            return
        if what == "camera":
            def work() -> str:
                result, error = client.ask({"action": "set_camera", "value": not item["on"]})
                if result is None:
                    return error
                return "Камера включена" if not item["on"] else "Камера выключена"
        elif what == "mic":
            def work() -> str:
                audio.set_mute("input", item["on"])  # on = sound is on, so the switch mutes it
                return "Микрофон выключен" if item["on"] else "Микрофон включён"
        elif what in ("wifi", "bluetooth"):
            def work() -> str:
                turn_on = not item["on"]
                word = "on" if turn_on else "off"
                command = (["nmcli", "radio", "wifi", word] if what == "wifi"
                           else ["bluetoothctl", "power", word])
                try:
                    done = subprocess.run(command, capture_output=True, timeout=15)
                except (OSError, subprocess.TimeoutExpired):
                    return "Не удалось переключить"
                name = "Wi-Fi" if what == "wifi" else "Bluetooth"
                if done.returncode != 0:
                    return f"{name}: не удалось переключить"
                return f"{name} включён" if turn_on else f"{name} выключен"
        else:
            return
        self._run(work)
