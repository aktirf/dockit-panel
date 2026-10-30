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
