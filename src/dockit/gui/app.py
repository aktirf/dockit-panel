"""Starts the window."""

from __future__ import annotations

import os
import sys
from pathlib import Path

QML_DIR = Path(__file__).parent / "qml"


def instance_socket_name() -> str:
    """Per-user local socket name so only one DOCKIT window process runs at a time."""
    return f"dockit-gui-{os.getuid()}"


def run(argv: list[str] | None = None, minimized: bool = False) -> int:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtNetwork import QLocalServer, QLocalSocket
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

    # Single-instance check: if another DOCKIT is already running (e.g. hidden in tray),
    # ask it to bring its window to the front and exit instead of creating a second process.
    socket_name = instance_socket_name()
    probe = QLocalSocket()
    probe.connectToServer(socket_name)
    if probe.waitForConnected(300):
        probe.write(b"show\n")
        probe.flush()
        probe.waitForBytesWritten(300)
        probe.disconnectFromServer()
        return 0
    probe.abort()

    QLocalServer.removeServer(socket_name)  # remove stale socket left by a crash
    server = QLocalServer(app)
    server.listen(socket_name)

    engine = QQmlApplicationEngine()
    backend = Backend()
    tray_avail = QSystemTrayIcon.isSystemTrayAvailable()
    if tray_avail:
        backend.set_tray_available(True)
    start_hidden = bool(minimized and backend.trayActive)
    app.aboutToQuit.connect(backend.shutdown)
    app.aboutToQuit.connect(server.close)
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("startHidden", start_hidden)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        print("Не удалось загрузить окно (смотрите сообщения выше).")
        return 1
    window = engine.rootObjects()[0]

    def show_window() -> None:
        window.show()
        window.raise_()
        window.requestActivate()

    def _on_second_instance() -> None:
        while server.hasPendingConnections():
            conn = server.nextPendingConnection()
            if conn is not None:
                conn.waitForReadyRead(200)
                conn.close()
                conn.deleteLater()
        show_window()

    server.newConnection.connect(_on_second_instance)
    window.visibleChanged.connect(lambda: backend.setWindowVisible(bool(window.isVisible())))
    if start_hidden:
        backend.setWindowVisible(False)

    tray = None
    if tray_avail:
        from .tray import Tray
        tray = Tray(app, window, backend)
    window.destroyed.connect(app.quit)      # closing the window really quits unless the tray keeps it
    result = app.exec()
    del tray
    return result
