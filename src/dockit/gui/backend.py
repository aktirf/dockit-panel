"""Qt side: runs scans in a worker thread and passes actions to the service.

The window never blocks: every slow thing (scan, polkit password dialog)
runs in a thread and reports back through signals.
"""

from __future__ import annotations

import subprocess
import threading
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
    _snapshot = Signal(object)   # worker thread -> main thread
    _finished = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._state = viewmodel.empty()
        self._toast = ""
        self._cpu = CpuMonitor()
        self._cpu_name = self._cpu.name()
        self._cpu_hist: deque = deque(maxlen=40)
        self._gpu_hist: deque = deque(maxlen=40)
        self._scenario = profiles.load_scenario()
        self._idle = idle.IdleWatcher()
        self._auto_last: str | None = None
        self._busy = False
        self._snapshot.connect(self._apply)
        self._finished.connect(self._done)
        self._timer = QTimer(self)
        self._timer.setInterval(3000)
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

    @Slot()
    def shutdown(self) -> None:
        self._idle.stop()

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
            if temp is not None:
                self._cpu_hist.append(temp)
            gpu_item = next((i for i in result.items if i.id == "gpu_nvidia"), None)
            if gpu_item and gpu_item.state and gpu_item.state.get("temp_c") is not None:
                self._gpu_hist.append(gpu_item.state["temp_c"])
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
                wanted = profiles.choose(rules, profiles.running_processes(), ac_online(),
                                         self._idle.reached())
                if wanted is None:
                    fallback = profiles.load_fallback()
                    wanted = fallback if fallback in available else None
                if wanted and wanted != self._auto_last:
                    self._auto_last = wanted
                    note = self._apply_profile(available[wanted])
            else:
                self._idle.stop()
            state = viewmodel.build(result, mode, cpu, self._cpu_name, self._cpu_hist, self._gpu_hist,
                                    muted, scenarios, self._scenario)
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

    @Slot(str, str, str, int)
    def saveRule(self, pid: str, programs: str, when: str, idle_minutes: int) -> None:
        available, _ = profiles.load()
        if pid not in available:
            return
        names = [n for n in programs.split(",") if n.strip()]
        try:
            profiles.save_rule(pid, names, when, idle_minutes)
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
