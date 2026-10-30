"""The root service: listens on a local socket and runs allowed actions.

Safety rules:
  * only actions listed in protocol.POLKIT_IDS exist, everything else is refused;
  * every changing action needs polkit approval for the process that asked
    (the desktop shows the usual password dialog);
  * input is size-limited and strictly validated in actions.py.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import socketserver
import struct
import subprocess
import sys
from typing import Callable

from . import actions
from .protocol import MAX_MESSAGE, POLKIT_IDS, SOCKET_PATH

# authorizer(polkit_action_id, pid, uid) -> (allowed, message)
Authorizer = Callable[[str, int, int], "tuple[bool, str]"]


def process_start_time(pid: int) -> str | None:
    """Start time of a process in clock ticks (field 22 of /proc/PID/stat).

    polkit wants it so a recycled PID cannot be mistaken for another process.
    """
    try:
        text = open(f"/proc/{pid}/stat", encoding="utf-8").read()
    except OSError:
        return None
    rest = text.rsplit(")", 1)[-1].split()  # rest[0] is field 3 (state)
    return rest[19] if len(rest) > 19 else None


def polkit_authorizer(action_id: str, pid: int, uid: int) -> tuple[bool, str]:
    start = process_start_time(pid)
    if start is None:
        return False, "Не удалось определить процесс, который отправил запрос."
    try:
        proc = subprocess.run(
            ["pkcheck", "--action-id", action_id,
             "--process", f"{pid},{start},{uid}", "--allow-user-interaction"],
            capture_output=True, text=True, timeout=130,
        )
    except FileNotFoundError:
        return False, "В системе нет pkcheck (пакет polkit)."
    except subprocess.TimeoutExpired:
        return False, "Время подтверждения истекло."
    if proc.returncode == 0:
        return True, ""
    return False, "Действие не подтверждено."


class Dispatcher:
    """Turns one raw request into one response. Pure logic, easy to test."""

    def __init__(self, authorizer: Authorizer = polkit_authorizer, log=None):
        self.authorizer = authorizer
        self.log = log or (lambda text: print(text, file=sys.stderr, flush=True))
        self.handlers = {
            "ping": lambda req: {"pong": True},
            "set_power_profile": lambda req: actions.set_power_profile(req.get("value")),
            "set_camera": lambda req: actions.set_camera(req.get("value")),
        }

    def handle(self, raw: bytes, pid: int, uid: int) -> dict:
        if len(raw) > MAX_MESSAGE:
            return {"ok": False, "error": "Запрос слишком длинный."}
        try:
            request = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {"ok": False, "error": "Запрос не похож на JSON."}
        if not isinstance(request, dict):
            return {"ok": False, "error": "Запрос должен быть объектом."}

        action = request.get("action")
        if not isinstance(action, str) or action not in POLKIT_IDS:
            return {"ok": False, "error": "Неизвестное действие."}

        polkit_id = POLKIT_IDS[action]
        if polkit_id is not None and uid != 0:
            allowed, message = self.authorizer(polkit_id, pid, uid)
            if not allowed:
                self.log(f"refused: action={action} uid={uid} pid={pid}")
                return {"ok": False, "error": message or "Нет разрешения."}

        try:
            result = self.handlers[action](request)
        except actions.ActionError as exc:
            self.log(f"failed: action={action} uid={uid} pid={pid} reason={exc}")
            return {"ok": False, "error": str(exc)}
        except Exception as exc:  # never crash the service because of one request
            self.log(f"error: action={action} {type(exc).__name__}")
            return {"ok": False, "error": "Внутренняя ошибка службы."}
        if polkit_id is not None:
            self.log(f"done: action={action} uid={uid} pid={pid} result={result}")
        return {"ok": True, "result": result}


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.request.settimeout(10)
        try:
            raw = self.rfile.readline(MAX_MESSAGE + 1)
        except (OSError, socket.timeout):
            return
        creds = self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        pid, uid, _gid = struct.unpack("3i", creds)
        response = self.server.dispatcher.handle(raw.rstrip(b"\r\n"), pid, uid)  # type: ignore[attr-defined]
        try:
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8") + b"\n")
        except OSError:
            pass


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

    def __init__(self, path: str, dispatcher: Dispatcher):
        self.dispatcher = dispatcher
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if os.path.exists(path):
            os.unlink(path)
        old_umask = os.umask(0o000)  # any local user may connect; polkit decides who may act
        try:
            super().__init__(path, _Handler)
        finally:
            os.umask(old_umask)


def _stop(_signum, _frame) -> None:
    raise SystemExit(0)  # lets `finally` below remove the socket file


def run(path: str = SOCKET_PATH) -> None:
    server = Server(path, Dispatcher())
    signal.signal(signal.SIGTERM, _stop)  # what `systemctl stop` sends
    print(f"dockit service listening on {path}", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if os.path.exists(path):
            os.unlink(path)
