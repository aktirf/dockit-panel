"""Tray icon (optional): quick menu for modes, scenarios and camera, plus live status tooltip."""

from __future__ import annotations

from ..core import i18n


def format_tooltip(state: dict, mode_names: dict[str, str], lang: str = "ru") -> str:
    """Short status text for the tray hover tooltip (pure logic, unit-tested)."""
    parts = ["DOCKIT"]
    mode = mode_names.get(state.get("currentMode", ""), "")
    if mode:
        parts.append(mode)
    cpu_temp = (state.get("cpu") or {}).get("temp")
    if cpu_temp and cpu_temp != "—":
        parts.append(f"CPU {cpu_temp} °C")
    gpu = state.get("gpu") or {}
    if gpu.get("asleep"):
        parts.append(i18n.tr("tray_gpu_asleep", lang))
    elif gpu.get("temp") and gpu.get("temp") != "—":
        parts.append(f"GPU {gpu['temp']} °C")
    return " · ".join(parts)


class Tray:
    def __init__(self, app, window, backend) -> None:
        from PySide6.QtGui import QAction, QIcon
        from PySide6.QtWidgets import QMenu, QSystemTrayIcon

        self._app = app
        self._window = window
        self._backend = backend
        self._last_menu_key = None

        icon = QIcon.fromTheme("dockit")
        if icon.isNull():
            icon = QIcon.fromTheme("preferences-system")
        if icon.isNull():                       # no icon theme: draw a small one
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QColor, QPainter, QPixmap
            pix = QPixmap(64, 64)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor("#1B2A3A"))
            painter.setPen(QColor("#5AB0FF"))
            painter.drawRoundedRect(4, 4, 56, 56, 14, 14)
            painter.setBrush(QColor("#5AB0FF"))
            painter.drawEllipse(26, 26, 12, 12)
            painter.end()
            icon = QIcon(pix)

        self._tray = QSystemTrayIcon(icon, app)
        self._tray.setToolTip("DOCKIT")
        self._menu = QMenu()
        self._show_action = QAction("Открыть DOCKIT", self._menu)
        self._show_action.triggered.connect(self.show_window)
        self._mode_menu = QMenu("Режим мощности", self._menu)
        self._scenario_menu = QMenu("Сценарий", self._menu)
        self._camera_action = QAction("Камера", self._menu)
        self._camera_action.triggered.connect(lambda: backend.toggle("camera"))
        self._quit_action = QAction("Выйти", self._menu)
        self._quit_action.triggered.connect(app.quit)

        self._menu.addAction(self._show_action)
        self._menu.addSeparator()
        self._menu.addMenu(self._mode_menu)
        self._menu.addMenu(self._scenario_menu)
        self._menu.addAction(self._camera_action)
        self._menu.addSeparator()
        self._menu.addAction(self._quit_action)

        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._clicked)
        backend.trayChanged.connect(self.sync)
        backend.stateChanged.connect(self.refresh_menu)
        backend.langChanged.connect(self.refresh_menu)
        self.sync()
        self.refresh_menu()

    def sync(self) -> None:
        self._tray.setVisible(bool(self._backend.trayActive))

    def refresh_menu(self) -> None:
        from PySide6.QtGui import QAction
        from . import viewmodel

        lang = getattr(self._backend, "lang", "ru")
        state = self._backend.state or {}
        mode_names = {m["id"]: m["name"] for m in viewmodel.modes_for_lang(lang)}
        self._tray.setToolTip(format_tooltip(state, mode_names, lang))

        modes = state.get("modes") or viewmodel.modes_for_lang(lang)
        cur_mode = state.get("currentMode") or ""
        scenarios = state.get("scenarios") or []
        cur_scenario = state.get("scenario") or ""
        toggles = {t.get("id"): t for t in (state.get("toggles") or []) if isinstance(t, dict)}
        cam = toggles.get("camera")

        menu_key = (
            lang,
            cur_mode,
            cur_scenario,
            tuple((s.get("id"), s.get("name")) for s in scenarios),
            (bool(cam and cam.get("can")), bool(cam and cam.get("on"))),
        )
        if menu_key == self._last_menu_key:
            return
        self._last_menu_key = menu_key

        self._show_action.setText(i18n.tr("tray_open", lang))
        self._mode_menu.setTitle(i18n.tr("power_mode", lang))
        self._scenario_menu.setTitle(i18n.tr("scenario", lang))
        self._quit_action.setText(i18n.tr("tray_quit", lang))

        self._mode_menu.clear()
        for m in modes:
            mid = str(m.get("id", ""))
            act = QAction(str(m.get("name", mid)), self._mode_menu)
            act.setCheckable(True)
            act.setChecked(mid == cur_mode)
            act.triggered.connect(lambda _=False, mode_id=mid: self._backend.setMode(mode_id))
            self._mode_menu.addAction(act)

        self._scenario_menu.clear()
        for s in scenarios:
            sid = str(s.get("id", ""))
            act = QAction(str(s.get("name", sid)), self._scenario_menu)
            act.setCheckable(True)
            act.setChecked(sid == cur_scenario)
            act.triggered.connect(lambda _=False, sc_id=sid: self._backend.setScenario(sc_id))
            self._scenario_menu.addAction(act)

        if cam and cam.get("can"):
            self._camera_action.setVisible(True)
            self._camera_action.setText(
                i18n.tr("tray_cam_off", lang) if cam.get("on") else i18n.tr("tray_cam_on", lang)
            )
        else:
            self._camera_action.setVisible(False)

    def show_window(self) -> None:
        self._window.show()
        self._window.raise_()
        self._window.requestActivate()

    def _clicked(self, reason) -> None:
        from PySide6.QtWidgets import QSystemTrayIcon
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window()
