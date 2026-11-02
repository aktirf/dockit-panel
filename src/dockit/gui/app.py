"""Starts the window."""

from __future__ import annotations

import os
import sys
from pathlib import Path

QML_DIR = Path(__file__).parent / "qml"


def run(argv: list[str] | None = None) -> int:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication, QSystemTrayIcon
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError:
        print("Для окна нужен PySide6. Установите: sudo pacman -S pyside6")
        print("Если вы используете виртуальное окружение, создайте его так:")
        print("  python -m venv --system-site-packages .venv")
        return 1

    from .backend import Backend

    app = QApplication(argv if argv is not None else sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("DOCKIT")
    app.setDesktopFileName("dockit")
    engine = QQmlApplicationEngine()
    backend = Backend()
    app.aboutToQuit.connect(backend.shutdown)
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        print("Не удалось загрузить окно (смотрите сообщения выше).")
        return 1
    window = engine.rootObjects()[0]
    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        from .tray import Tray
        backend.set_tray_available(True)
        tray = Tray(app, window, backend)
    window.destroyed.connect(app.quit)      # closing the window really quits unless the tray keeps it
    result = app.exec()
    del tray
    return result
