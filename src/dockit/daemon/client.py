"""Talk to the service from the command line or the window."""

from __future__ import annotations

import json
import socket

from .protocol import MAX_MESSAGE, SOCKET_PATH


class DaemonUnavailable(Exception):
    """The service is not running or the socket cannot be reached."""


def request(payload: dict, path: str = SOCKET_PATH, timeout: float = 130) -> dict:
    """Send one request, return the whole response dict ({"ok": ..., ...})."""
    data = json.dumps(payload).encode("utf-8")
    if len(data) > MAX_MESSAGE:
        raise ValueError("request too long")
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(path)
            sock.sendall(data + b"\n")
            reply = b""
            while not reply.endswith(b"\n"):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                reply += chunk
    except (FileNotFoundError, ConnectionRefusedError, PermissionError, socket.timeout) as exc:
        raise DaemonUnavailable(str(exc)) from exc
    try:
        return json.loads(reply.decode("utf-8"))
    except ValueError as exc:
        raise DaemonUnavailable("unreadable reply from the service") from exc


def daemon_running(path: str = SOCKET_PATH) -> bool:
    try:
        return bool(request({"action": "ping"}, path, timeout=2).get("ok"))
    except DaemonUnavailable:
        return False


_DAEMON_ERROR_KEYS = {
    "Действие не подтверждено.": "err_polkit_refused",
    "Нужно подтверждение паролем: примените профиль вручную.": "err_polkit_quiet",
    "Время подтверждения истекло.": "err_polkit_timeout",
    "В системе нет pkcheck (пакет polkit).": "err_polkit_missing",
    "Внутренняя ошибка службы.": "err_internal",
}


def localize_daemon_error(text: str, lang: str = "ru") -> str:
    """Translate known service/polkit messages when the GUI runs in a non-Russian locale."""
    if lang == "ru":
        return text
    key = _DAEMON_ERROR_KEYS.get(text)
    if key:
        from ..core import i18n
        return i18n.tr(key, lang)
    return text


def ask(payload: dict, path: str = SOCKET_PATH, lang: str = "ru") -> tuple[dict | None, str]:
    """Send a request. Returns (result, "") on success or (None, localized error message)."""
    from ..core import i18n

    try:
        response = request(payload, path)
    except DaemonUnavailable:
        return None, i18n.tr("err_daemon_stopped", lang)
    if not response.get("ok"):
        raw = str(response.get("error") or i18n.tr("err_unknown", lang))
        return None, localize_daemon_error(raw, lang)
    return response.get("result", {}), ""
