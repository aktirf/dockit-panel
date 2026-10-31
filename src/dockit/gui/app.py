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
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError:
        print("Для окна нужен PySide6. Установите: sudo pacman -S pyside6")
        print("Если вы используете виртуальное окружение, создайте его так:")
        print("  python -m venv --system-site-packages .venv")
        return 1

    from .backend import Backend

    app = QGuiApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("DOCKIT")
    app.setDesktopFileName("dockit")
    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        print("Не удалось загрузить окно (смотрите сообщения выше).")
        return 1
    return app.exec()
