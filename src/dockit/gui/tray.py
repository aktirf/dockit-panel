"""Tray icon (optional): shows the window again and lets the user quit."""

from __future__ import annotations


class Tray:
    def __init__(self, app, window, backend) -> None:
        from PySide6.QtGui import QAction, QIcon
        from PySide6.QtWidgets import QMenu, QSystemTrayIcon

        self._window = window
        self._backend = backend
        icon = QIcon.fromTheme("dockit")
        if icon.isNull():
            icon = QIcon.fromTheme("preferences-system")
        self._tray = QSystemTrayIcon(icon, app)
        self._tray.setToolTip("DOCKIT")
        menu = QMenu()
        show = QAction("Открыть DOCKIT", menu)
        show.triggered.connect(self.show_window)
        quit_ = QAction("Выйти", menu)
        quit_.triggered.connect(app.quit)
        menu.addAction(show)
        menu.addAction(quit_)
        self._menu = menu
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._clicked)
        backend.trayChanged.connect(self.sync)
        self.sync()

    def sync(self) -> None:
        self._tray.setVisible(bool(self._backend.trayActive))

    def show_window(self) -> None:
        self._window.show()
        self._window.raise_()
        self._window.requestActivate()

    def _clicked(self, reason) -> None:
        from PySide6.QtWidgets import QSystemTrayIcon
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window()
