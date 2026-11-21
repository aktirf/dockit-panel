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

from ..core import audio, i18n, kbd_backlight, periph_battery, processes, profiles, session_state, sysfs
from ..core import idle
from ..core import bluetooth, gpu_power, tuning
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
    langChanged = Signal()
    trayChanged = Signal()
    profileCreated = Signal(str)
    logChanged = Signal()
    _snapshot = Signal(object)   # worker thread -> main thread
    _finished = Signal(str)
    _logLoaded = Signal()

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
        self._top = processes.TopCpu()
        self._bat_hist = self._load_bat_hist()
        self._bat_at = 0.0
        self._scenario = profiles.load_scenario()
        self._idle = idle.IdleWatcher()
        self._auto_last: str | None = None
        self._busy = False
        self._refresh_queued = False
        self._window_visible = True
        self._toggle_busy: set[str] = set()
        self._periph_at = -999.0
        self._periph_cache: tuple[list, object] = ([], None)
        self._pending_bright: tuple[float, int] | None = None
        self._pending_vol: tuple[float, int] | None = None
        self._pending_kbd: tuple[float, dict] | None = None
        self._kbd_saved = self._load_kbd_saved()
        self._hist_at = 0.0
        self._snapshot.connect(self._apply)
        self._finished.connect(self._done)
        self._logLoaded.connect(self.logChanged)
        self._timer = QTimer(self)
        self._settings = self._load_settings()
        self._timer.setInterval(self._settings["interval"] * 1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()
        if session_state.has_saved():
            self._restore_session_on_start()

    def _restore_session_on_start(self) -> None:
        """Quietly re-apply saved refresh rate, power mode, and keyboard RGB on login/startup."""
        include_pr = self._scenario != "auto"

        def target():
            def quiet_ask(payload: dict):
                res, _ = client.ask(dict(payload, interactive=False))
                return res

            try:
                applied = session_state.restore(quiet_ask, include_power_and_refresh=include_pr)
            except Exception:
                return
            if applied:
                self._tuning_at = 0
                self._display_at = 0
                self._finished.emit("")

        threading.Thread(target=target, daemon=True).start()

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
    ACCENTS = {
        "blue": "#5AB0FF",
        "mint": "#4CC38A",
        "purple": "#A78BFA",
        "amber": "#F5B942",
        "coral": "#FF7A7A",
    }
    DEFAULTS = {
        "interval": 3, "warn_temp": 90, "notify": True, "tray": False,
        "accent": "blue", "compact_nav": False, "lang": "auto",
    }

    @staticmethod
    def _settings_path() -> str:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return os.path.join(base, "dockit", "settings.json")

    @staticmethod
    def _autostart_path() -> str:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return os.path.join(base, "autostart", "dockit.desktop")

    @staticmethod
    def _kbd_path() -> str:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return os.path.join(base, "dockit", "kbd_backlight.json")

    def _load_kbd_saved(self) -> dict:
        data = {"on": True, "brightness": 100, "color": "#5AB0FF", "autonomous": False}
        try:
            with open(self._kbd_path(), encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded.get("on"), bool):
                data["on"] = loaded["on"]
            if isinstance(loaded.get("autonomous"), bool):
                data["autonomous"] = loaded["autonomous"]
            b = loaded.get("brightness")
            if isinstance(b, int) and not isinstance(b, bool) and 0 <= b <= 100:
                data["brightness"] = b
            c = loaded.get("color")
            if isinstance(c, str):
                data["color"] = kbd_backlight.normalize_hex_color(c)
        except (OSError, ValueError, AttributeError):
            pass
        return data

    def _save_kbd_saved(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._kbd_path()), exist_ok=True)
            with open(self._kbd_path(), "w", encoding="utf-8") as f:
                json.dump(self._kbd_saved, f)
        except OSError:
            pass

    def _load_settings(self) -> dict:
        data = dict(self.DEFAULTS)
        try:
            with open(self._settings_path(), encoding="utf-8") as f:
                loaded = json.load(f)
            if loaded.get("interval") in (1, 3, 5, 10):
                data["interval"] = loaded["interval"]
            if loaded.get("warn_temp") in (0, 80, 85, 90, 95):
                data["warn_temp"] = loaded["warn_temp"]
            if loaded.get("accent") in self.ACCENTS:
                data["accent"] = loaded["accent"]
            if loaded.get("lang") in ("auto", *i18n.SUPPORTED):
                data["lang"] = loaded["lang"]
            for key in ("notify", "tray", "compact_nav"):
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
        self._state = dict(self._state, settings=self._settings_view())
        self.settingsChanged.emit()
        self.stateChanged.emit()

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

    def _lang(self) -> str:
        return i18n.resolve_lang(self._settings.get("lang"))

    @Property(str, notify=langChanged)
    def lang(self) -> str:
        return self._lang()

    @Property("QVariantMap", notify=langChanged)
    def t(self) -> dict:
        return i18n.catalog(self._lang())

    @Slot(str)
    def setLang(self, value: str) -> None:
        if value not in ("auto", *i18n.SUPPORTED):
            return
        self._settings["lang"] = value
        self._save_settings()
        self.langChanged.emit()
        self._sync_profiles_now()
        self.refresh()

    @Property(str, notify=settingsChanged)
    def accentColor(self) -> str:
        return self.ACCENTS.get(self._settings.get("accent", "blue"), "#5AB0FF")

    @Property(str, constant=True)
    def version(self) -> str:
        from .. import __version__
        return __version__

    def set_tray_available(self, value: bool) -> None:
        self._tray_available = value
        self.trayChanged.emit()

    def _sync_timer_interval(self) -> None:
        base = self._settings["interval"]
        # When hidden in tray, slow down polling so DOCKIT saves battery while still running auto rules.
        secs = base if self._window_visible else max(10, base)
        self._timer.setInterval(secs * 1000)

    def setWindowVisible(self, visible: bool) -> None:
        visible = bool(visible)
        if visible == self._window_visible:
            return
        self._window_visible = visible
        self._sync_timer_interval()
        if visible:
            self.refresh()

    @Slot(int)
    def setInterval(self, seconds: int) -> None:
        if seconds not in (1, 3, 5, 10):
            return
        self._settings["interval"] = seconds
        self._sync_timer_interval()
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

    @Slot(str)
    def setAccent(self, accent: str) -> None:
        if accent not in self.ACCENTS:
            return
        self._settings["accent"] = accent
        self._save_settings()
        self.refresh()

    @Slot(bool)
    def setCompactNav(self, value: bool) -> None:
        self._settings["compact_nav"] = bool(value)
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
                self._say("Автозапуск включён. Если окно не появится при входе, добавьте в конфиг: "
                          "в Hyprland строку exec-once = dockit gui, в niri spawn-at-startup \"dockit\" \"gui\"")
            elif os.path.exists(path):
                os.remove(path)
                self._say("Автозапуск выключен")
        except OSError:
            self._say("Не удалось изменить автозапуск")
        self.settingsChanged.emit()
        self.refresh()

    def _bluetooth_and_periph_batteries(self, lang: str) -> tuple[list, list]:
        now = time.monotonic()
        if now - getattr(self, "_bt_at", -999) > 20:
            self._bt_at = now
            raw_bt = bluetooth.connected_devices()
            bt_list = [{"name": d["name"], "battery": -1 if d["battery"] is None else d["battery"],
                        "icon": d.get("icon", "")} for d in raw_bt]
            raw_bats = periph_battery.collect(bluetooth_devices=bt_list)
            self._bt_cache = [{"name": d["name"], "battery": d["battery"]}
                              for d in periph_battery.enrich_bluetooth(bt_list, raw_bats)]
            self._pbat_cache = raw_bats
        return list(getattr(self, "_bt_cache", [])), viewmodel.periph_batteries_view(
            getattr(self, "_pbat_cache", []), lang
        )

    @Property(str, notify=logChanged)
    def logText(self) -> str:
        return getattr(self, "_log_text", "")

    @Slot()
    def loadLog(self) -> None:
        def target():
            try:
                proc = subprocess.run(["journalctl", "-u", "dockit", "-n", "40", "--no-pager"],
                                      capture_output=True, text=True, timeout=8)
                text = proc.stdout.strip() or proc.stderr.strip() or "Журнал пуст."
            except (OSError, subprocess.TimeoutExpired):
                text = "Не удалось прочитать журнал (нужна команда journalctl)."
            self._log_text = text
            self._logLoaded.emit()

        threading.Thread(target=target, daemon=True).start()

    @Slot()
    def copyLog(self) -> None:
        from PySide6.QtGui import QGuiApplication
        text = getattr(self, "_log_text", "")
        if not text:
            self._say("Сначала нажмите «Обновить», чтобы загрузить журнал")
            return
        QGuiApplication.clipboard().setText(text)
        self._say("Журнал службы скопирован в буфер обмена")

    @Slot(str)
    def installFix(self, feature_id: str) -> None:
        packages = viewmodel.FIX_PACKAGES.get(feature_id)
        if not packages or shutil.which("pkexec") is None or shutil.which("pacman") is None:
            self._say("Автоматическая установка недоступна на этой системе")
            return

        def work() -> str:
            proc = subprocess.run(["pkexec", "pacman", "-S", "--needed", "--noconfirm", *packages],
                                  capture_output=True, text=True, timeout=900)
            if proc.returncode == 0:
                return "Установлено: " + ", ".join(packages) + ". Если функция не появилась, перезапустите DOCKIT."
            return "Не удалось установить (пароль не введён или нет сети)."

        self._say("Устанавливаю " + ", ".join(packages) + "…")
        self._run(work)

    @Slot(str, str)
    def setAudio(self, kind: str, description: str) -> None:
        if kind not in ("output", "input"):
            return

        def work() -> str:
            try:
                device = audio.set_default(kind, description)
            except audio.AudioError as exc:
                return str(exc)
            return ("Звук: " if kind == "output" else "Микрофон: ") + device.description

        self._run(work)

    @Slot(int)
    def setVolume(self, percent: int) -> None:
        percent = max(0, min(150, int(percent)))
        self._pending_vol = (time.monotonic() + 2.0, percent)
        audio_state = dict(self._state.get("audio") or {})
        audio_state["outputVolume"] = percent
        self._state = dict(self._state, audio=audio_state)
        self.stateChanged.emit()

        def work() -> str:
            try:
                audio.set_volume("output", percent)
            except audio.AudioError as exc:
                return str(exc)
            return f"Громкость: {percent} %"

        self._run(work)

    @Slot()
    def toggleMuteOutput(self) -> None:
        cur_muted = bool((self._state.get("audio") or {}).get("outputMuted", False))
        audio_state = dict(self._state.get("audio") or {})
        audio_state["outputMuted"] = not cur_muted
        self._state = dict(self._state, audio=audio_state)
        self.stateChanged.emit()

        def work() -> str:
            try:
                audio.set_mute("output", not cur_muted)
            except audio.AudioError as exc:
                return str(exc)
            return "Звук выключен" if not cur_muted else "Звук включён"

        self._run(work)

    def _tuning(self) -> dict:
        now = time.monotonic()
        if now - getattr(self, "_tuning_at", 0) > 10 or not hasattr(self, "_tuning_cache"):
            self._tuning_at = now
            data = {"boost": tuning.read_boost(), "epp": tuning.read_epp(), "eppChoices": tuning.epp_choices()}
            if now - getattr(self, "_gpu_lim_at", -999) > 60 and not gpu_power.gpu_asleep():
                # nvidia-smi would wake a sleeping card: keep the old value meanwhile
                self._gpu_lim_at = now
                self._gpu_lim = tuning.gpu_power_limits()
            data["gpuLimit"] = getattr(self, "_gpu_lim", None)
            self._tuning_cache = data
        return dict(self._tuning_cache)

    @staticmethod
    def _bat_path() -> str:
        base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
        return os.path.join(base, "dockit", "battery.json")

    def _load_bat_hist(self) -> list:
        try:
            with open(self._bat_path(), encoding="utf-8") as f:
                data = json.load(f)
            cutoff = time.time() - 24 * 3600
            return [[t, p] for t, p in data if isinstance(t, (int, float)) and isinstance(p, int) and t >= cutoff]
        except (OSError, ValueError, TypeError):
            return []

    def _battery_history(self, percent) -> list:
        """Charge level every 5 minutes for the last 24 hours (kept in ~/.local/state/dockit)."""
        now = time.time()
        if percent is not None and now - self._bat_at >= 300:
            self._bat_at = now
            self._bat_hist = [e for e in self._bat_hist if e[0] >= now - 24 * 3600] + [[now, int(percent)]]
            try:
                os.makedirs(os.path.dirname(self._bat_path()), exist_ok=True)
                with open(self._bat_path(), "w", encoding="utf-8") as f:
                    json.dump(self._bat_hist, f)
            except OSError:
                pass
        return [p for _, p in self._bat_hist]

    @Slot(bool)
    def setBoost(self, value: bool) -> None:
        val = bool(value)
        t = dict(self._state.get("tuning") or {})
        t["boost"] = val
        self._state = dict(self._state, tuning=t)
        self.stateChanged.emit()

        def work() -> str:
            result, error = client.ask({"action": "set_boost", "value": val})
            self._tuning_at = 0
            return "Turbo Boost " + ("включён" if val else "выключен") if result is not None else error

        self._run(work)

    @Slot(str)
    def setEpp(self, value: str) -> None:
        t = dict(self._state.get("tuning") or {})
        t["epp"] = value
        self._state = dict(self._state, tuning=t)
        self.stateChanged.emit()

        def work() -> str:
            result, error = client.ask({"action": "set_epp", "value": value})
            self._tuning_at = 0
            return f"Энергопотребление процессора: {value}" if result is not None else error

        self._run(work)

    @Slot(int)
    def setGpuLimit(self, watts: int) -> None:
        def work() -> str:
            result, error = client.ask({"action": "set_gpu_power_limit", "value": watts})
            self._tuning_at = 0
            self._gpu_lim_at = -999
            return f"Лимит видеокарты: {watts} Вт" if result is not None else error

        self._run(work)

    def _display(self) -> dict:
        from ..core import display
        now = time.monotonic()
        if now - getattr(self, "_display_at", 0) > 10 or not hasattr(self, "_display_cache"):
            self._display_at = now
            info = display.refresh_info()
            self._display_cache = {"brightness": display.brightness_percent(),
                                   "refresh": info["current"], "rates": info["rates"]}
        return dict(self._display_cache)

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
        lang = self._lang()
        fix_lbl = i18n.tr("report_fix", lang)
        st = self._state
        lines = [f"DOCKIT {self.version}", ", ".join(f"{k}: {v}" for k, v in st.get("system", {}).items()), ""]
        for f in st.get("features", []):
            lines.append(f"[{f['statusText']}] {f['name']}: {f['detail']}")
            if f.get("hint"):
                lines.append(f"    {fix_lbl}: {f['hint']}")
        QGuiApplication.clipboard().setText("\n".join(lines))
        self._say(i18n.tr("report_copied", lang))

    @Slot()
    def shutdown(self) -> None:
        self._idle.stop()

    @Slot(str, result=str)
    def describeProgram(self, name: str) -> str:
        return processes.describe(name)

    @Slot(str, result=str)
    def describeToggle(self, what: str) -> str:
        key = {
            "camera": "tip_toggle_camera",
            "mic": "tip_toggle_mic",
            "wifi": "tip_toggle_wifi",
            "bluetooth": "tip_toggle_bluetooth",
        }.get(what, "")
        return i18n.tr(key, self._lang()) if key else ""

    # ---- scanning ----
    @Slot()
    def refresh(self) -> None:
        if self._busy:
            self._refresh_queued = True
            return
        self._busy = True
        threading.Thread(target=self._collect, daemon=True).start()

    def _collect(self) -> None:
        try:
            now = time.monotonic()
            need_periph = (now - self._periph_at >= 20) or not self._periph_cache[0]
            result = scan(peripherals=need_periph)
            if need_periph:
                self._periph_at = now
                self._periph_cache = (result.peripherals, result.laptop)
            else:
                result.peripherals, result.laptop = self._periph_cache
            mode = sysfs.read_text(PROFILE)
            cpu = self._cpu.sample()
            sensors = next((i for i in result.items if i.id == "sensors"), None)
            temp = viewmodel.cpu_temperature(sensors.state if sensors else None)
            min_gap = max(0.8, self._settings["interval"] - 0.3)
            fresh = now - self._hist_at >= min_gap
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
            audio_item = next((i for i in result.items if i.id == "audio"), None)
            audio_devices = audio_item.state if audio_item and isinstance(audio_item.state, list) else []
            muted = next((d["muted"] for d in audio_devices if d.get("kind") == "input" and d.get("default")), None)
            lang = self._lang()
            available, rules = profiles.load()
            scenarios = [{"id": p.id, "name": viewmodel.profile_display_name(p, lang)} for p in available.values()]
            scenarios.append({"id": "auto", "name": i18n.tr("scenario_auto", lang)})
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
                    note = self._apply_profile(available[wanted], interactive=False)
                    self._log(f"Авто: «{available[wanted].name}» ({reason})")
                    if not first:
                        self._notify("DOCKIT", f"Включён профиль «{available[wanted].name}»: {reason}")
            else:
                self._idle.stop()
            state = viewmodel.build(result, mode, cpu, self._cpu_name, self._cpu_hist, self._gpu_hist,
                                    muted, scenarios, self._scenario, lang=lang, kbd_saved=dict(self._kbd_saved))
            bt_list, pbat_list = self._bluetooth_and_periph_batteries(lang)
            state["bluetooth"] = bt_list
            state["periphBatteries"] = pbat_list
            state["display"] = self._display()
            if fresh:
                self._top_cache = self._top.sample()
            state["top"] = getattr(self, "_top_cache", [])
            state["tuning"] = self._tuning()
            state["batteryHistory"] = self._battery_history(state["battery"].get("percent"))
            state["cooling"] = cooling
            state["journal"] = list(reversed(self._journal))[:6]
            state["settings"] = self._settings_view()
            state["profiles"] = viewmodel.profile_cards(available, rules, lang=lang)
            state["apps"] = processes.user_programs()
            state["idleAvailable"] = idle.available()
            fb = profiles.load_fallback()
            state["fallback"] = fb if fb in available else ""
            def_out = next((d for d in audio_devices if d.get("kind") == "output" and d.get("default")), None)
            def_in = next((d for d in audio_devices if d.get("kind") == "input" and d.get("default")), None)
            state["audio"] = {
                "outputs": [d["description"] for d in audio_devices if d.get("kind") == "output"],
                "inputs": [d["description"] for d in audio_devices if d.get("kind") == "input"],
                "outputDefault": def_out["description"] if def_out else "",
                "inputDefault": def_in["description"] if def_in else "",
                "outputVolume": def_out["volume"] if (def_out and def_out.get("volume") is not None) else -1,
                "outputMuted": bool(def_out.get("muted")) if def_out else False,
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
            now = time.monotonic()
            # Ignore stale brightness/volume from an in-flight scan started before a slider release.
            if self._pending_bright is not None:
                until, target = self._pending_bright
                disp = state.get("display") or {}
                cur = disp.get("brightness")
                if now >= until or (cur is not None and abs(int(cur) - target) <= 1):
                    self._pending_bright = None
                elif cur is not None:
                    state["display"] = dict(disp, brightness=target)
            if self._pending_vol is not None:
                until, target = self._pending_vol
                aud = state.get("audio") or {}
                cur = aud.get("outputVolume")
                if now >= until or (cur is not None and cur >= 0 and abs(int(cur) - target) <= 1):
                    self._pending_vol = None
                elif cur is not None and cur >= 0:
                    state["audio"] = dict(aud, outputVolume=target)
            if self._pending_kbd is not None:
                until, target = self._pending_kbd
                kbd = state.get("kbdBacklight") or {}
                if now >= until:
                    self._pending_kbd = None
                elif kbd.get("available"):
                    state["kbdBacklight"] = dict(kbd, **target)
            self._state = state
            self.stateChanged.emit()
        if self._refresh_queued:
            self._refresh_queued = False
            self.refresh()

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

    def _apply_profile(self, profile: profiles.Profile, interactive: bool = True) -> str:
        """interactive=False (automatic switching) never pops up a password dialog."""
        errors: list[str] = []

        def ask(payload: dict):
            if not interactive:
                payload = dict(payload, interactive=False)
            result, error = client.ask(payload)
            if result is None:
                errors.append(error)
            return result

        profiles.apply(profile, ask, errors=errors)
        if profile.power:
            time.sleep(0.08)
        self._tuning_at = 0
        self._display_at = 0
        if interactive:
            updates: dict = {}
            if profile.power:
                updates["power"] = profile.power
            if profile.refresh:
                updates["refresh"] = int(profile.refresh)
            if updates:
                session_state.save(updates)
        if errors:
            return f"Профиль «{profile.name}»: {errors[0]}"
        return f"Профиль «{profile.name}» включён"

    @Slot(str)
    def setMode(self, mode: str) -> None:
        if mode not in profiles.POWER_VALUES:
            return
        self._state = dict(self._state, currentMode=mode)
        self.stateChanged.emit()

        def work() -> str:
            result, error = client.ask({"action": "set_power_profile", "value": mode})
            if result is not None:
                session_state.save({"power": mode})
                time.sleep(0.08)  # let kernel amd_pstate update EPP choices before refresh
                self._tuning_at = 0
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

    def _sync_profiles_now(self) -> None:
        """Immediately reflect profile/rule/language edits in the UI without waiting for the next scan."""
        lang = self._lang()
        available, rules = profiles.load()
        scenarios = [{"id": p.id, "name": viewmodel.profile_display_name(p, lang)} for p in available.values()]
        scenarios.append({"id": "auto", "name": i18n.tr("scenario_auto", lang)})
        fb = profiles.load_fallback()
        self._state = dict(
            self._state,
            modes=viewmodel.modes_for_lang(lang),
            profiles=viewmodel.profile_cards(available, rules, lang=lang),
            scenarios=scenarios,
            fallback=fb if fb in available else "",
        )
        self.stateChanged.emit()

    @Slot(str, str, str, str, str, int, int)
    def saveProfile(self, pid: str, power: str, camera: str, output: str, mic: str,
                    brightness: int, refresh: int) -> None:
        available, _ = profiles.load()
        if pid not in available:
            return
        try:
            profiles.save_profile(pid, power, camera, output, mic, brightness=brightness, refresh=refresh)
        except (ValueError, OSError):
            self._say("Не удалось сохранить профиль")
            return
        self._sync_profiles_now()
        if self._scenario == pid:
            self._say(f"Профиль «{available[pid].name}» сохранён. Нажмите «Применить изменения», чтобы обновить.")
        else:
            self._say(f"Профиль «{available[pid].name}» сохранён.")
        self.refresh()

    @Slot(str)
    def createProfile(self, name: str) -> None:
        try:
            pid = profiles.create_profile(name)
        except (ValueError, OSError):
            self._say("Не удалось создать профиль (название от 1 до 30 символов)")
            return
        self._sync_profiles_now()
        self._say(f"Профиль «{name.strip()}» создан. Настройте его справа.")
        self.profileCreated.emit(pid)
        self.refresh()

    @Slot(str)
    def deleteProfile(self, pid: str) -> None:
        try:
            profiles.delete_profile(pid)
        except (ValueError, OSError):
            self._say("Не удалось удалить профиль")
            return
        if self._scenario == pid:
            self.setScenario("auto")
        self._sync_profiles_now()
        self._say("Профиль удалён")
        self.refresh()

    @Slot(int)
    def setBrightness(self, percent: int) -> None:
        percent = max(1, min(100, int(percent)))
        self._pending_bright = (time.monotonic() + 2.0, percent)
        disp = dict(self._state.get("display") or {})
        disp["brightness"] = percent
        self._display_cache = dict(getattr(self, "_display_cache", disp), brightness=percent)
        self._state = dict(self._state, display=disp)
        self.stateChanged.emit()

        def work() -> str:
            from ..core import display
            if display.set_brightness_user(percent) is None:  # logind, no password
                self._display_at = 0
                return f"Яркость: {percent} %"
            result, error = client.ask({"action": "set_brightness", "value": percent})
            self._display_at = 0
            return f"Яркость: {percent} %" if result is not None else error

        self._run(work)

    @Slot(int)
    def setRefresh(self, hz: int) -> None:
        hz = int(hz)
        disp = dict(self._state.get("display") or {})
        disp["refresh"] = hz
        self._display_cache = dict(getattr(self, "_display_cache", disp), refresh=hz)
        self._state = dict(self._state, display=disp)
        self.stateChanged.emit()

        def work() -> str:
            from ..core import display
            self._display_at = 0
            err = display.set_refresh(hz)
            if err is None:
                session_state.save({"refresh": hz})
            return err or f"Частота экрана: {hz} Гц"

        self._run(work)

    @Slot(bool, int, str, bool)
    def setKbdBacklight(self, on: bool, brightness: int, color: str, autonomous: bool) -> None:
        brightness = max(0, min(100, int(brightness)))
        try:
            norm_color = kbd_backlight.normalize_hex_color(color)
        except ValueError:
            norm_color = self._kbd_saved.get("color", "#5AB0FF")
        payload = {
            "on": bool(on),
            "brightness": brightness,
            "color": norm_color,
            "autonomous": bool(autonomous),
        }
        self._kbd_saved = dict(payload)
        self._save_kbd_saved()
        session_state.save({"kbd_backlight": payload})
        self._pending_kbd = (time.monotonic() + 2.0, dict(payload))
        kbd = dict(self._state.get("kbdBacklight") or {})
        kbd.update(payload)
        self._state = dict(self._state, kbdBacklight=kbd)
        self.stateChanged.emit()

        lang = self._lang()

        def work() -> str:
            result, error = client.ask({"action": "set_kbd_backlight", "value": payload})
            if result is None:
                return error
            if result.get("autonomous"):
                return i18n.tr("kbd_toast_auto", lang)
            if not result.get("on"):
                return i18n.tr("kbd_toast_off", lang)
            if result.get("rgb"):
                return i18n.tr("kbd_toast_rgb", lang, color=result.get("color", norm_color), pct=result.get("brightness", brightness))
            return i18n.tr("kbd_toast_led", lang, pct=result.get("brightness", brightness))

        self._run(work)

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
        self._sync_profiles_now()
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
        self._sync_profiles_now()
        self._say("Сохранено")
        self.refresh()

    @Slot(str)
    def toggle(self, what: str) -> None:
        if what in self._toggle_busy:
            return
        items = {t["id"]: t for t in self._state.get("toggles", [])}
        item = items.get(what)
        if item is None or not item.get("can"):
            return
        self._toggle_busy.add(what)
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
                if what == "bluetooth" and turn_on and shutil.which("rfkill"):
                    # Best-effort unblock in case Bluetooth was soft-blocked via rfkill.
                    try:
                        subprocess.run(["rfkill", "unblock", "bluetooth"], capture_output=True, timeout=5)
                    except (OSError, subprocess.TimeoutExpired):
                        pass
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
            self._toggle_busy.discard(what)
            return

        def guarded() -> str:
            try:
                return work()
            finally:
                self._toggle_busy.discard(what)

        self._run(guarded)
