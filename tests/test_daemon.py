import json
import os
import re
import tempfile
import threading
from pathlib import Path

import pytest

from dockit.daemon import actions, server
from dockit.daemon.client import DaemonUnavailable, daemon_running, request
from dockit.daemon.protocol import MAX_MESSAGE
from dockit.peripherals.database import DeviceEntry


# ---------- power profile ----------

def _profile_files(tmp_path, current="balanced", choices="low-power balanced performance"):
    profile = tmp_path / "platform_profile"
    profile.write_text(current + "\n")
    options = tmp_path / "platform_profile_choices"
    options.write_text(choices + "\n")
    return str(profile), str(options)


def test_set_power_profile_ok(tmp_path):
    profile, options = _profile_files(tmp_path)
    result = actions.set_power_profile("performance", profile, options)
    assert result == {"profile": "performance"}


@pytest.mark.parametrize("bad", ["turbo", "", "performance; rm -rf /", "../x", None, 5, ["performance"]])
def test_set_power_profile_rejects_bad_values(tmp_path, bad):
    profile, options = _profile_files(tmp_path)
    with pytest.raises(actions.ActionError):
        actions.set_power_profile(bad, profile, options)
    assert Path(profile).read_text().strip() == "balanced"  # nothing was written


def test_set_power_profile_unsupported_model(tmp_path):
    with pytest.raises(actions.ActionError):
        actions.set_power_profile("balanced", str(tmp_path / "none"), str(tmp_path / "none2"))


def test_sync_power_state_unlocks_governor_when_ppd_absent(tmp_path):
    cpu0 = tmp_path / "cpu0" / "cpufreq"
    cpu1 = tmp_path / "cpu1" / "cpufreq"
    cpu0.mkdir(parents=True)
    cpu1.mkdir(parents=True)
    (cpu0 / "scaling_driver").write_text("amd-pstate-epp\n")
    (cpu0 / "scaling_available_governors").write_text("performance powersave\n")
    (cpu0 / "scaling_governor").write_text("performance\n")
    (cpu1 / "scaling_governor").write_text("performance\n")

    actions._sync_power_state("balanced", cpu_base=str(tmp_path), use_ppd=False)
    assert (cpu0 / "scaling_governor").read_text() == "powersave"
    assert (cpu1 / "scaling_governor").read_text() == "powersave"

    actions._sync_power_state("performance", cpu_base=str(tmp_path), use_ppd=False)
    assert (cpu0 / "scaling_governor").read_text() == "performance"
    assert (cpu1 / "scaling_governor").read_text() == "performance"


# ---------- camera ----------

CAMERA = DeviceEntry(name="Cam", kind="camera", usb_id="3277:00b2")
MOUSE = DeviceEntry(name="Mouse", kind="mouse", usb_id="379a:3608")


def _usb(base, port, vendor, product, authorized="1"):
    d = base / port
    d.mkdir(parents=True)
    (d / "idVendor").write_text(vendor + "\n")
    (d / "idProduct").write_text(product + "\n")
    (d / "authorized").write_text(authorized + "\n")


def test_camera_switch_touches_only_cameras(tmp_path):
    _usb(tmp_path, "3-1", "3277", "00b2")
    _usb(tmp_path, "1-4", "379a", "3608")
    state = actions.set_camera(False, str(tmp_path), [CAMERA, MOUSE])
    assert state["cameras"] == [{"usb_id": "3277:00b2", "port": "3-1", "enabled": False}]
    assert (tmp_path / "3-1" / "authorized").read_text() == "0"
    assert (tmp_path / "1-4" / "authorized").read_text().strip() == "1"  # mouse untouched
    state = actions.set_camera(True, str(tmp_path), [CAMERA, MOUSE])
    assert state["cameras"][0]["enabled"] is True


@pytest.mark.parametrize("bad", ["yes", 1, 0, None, "false"])
def test_camera_requires_real_boolean(tmp_path, bad):
    _usb(tmp_path, "3-1", "3277", "00b2")
    with pytest.raises(actions.ActionError):
        actions.set_camera(bad, str(tmp_path), [CAMERA])
    assert (tmp_path / "3-1" / "authorized").read_text().strip() == "1"


def test_camera_not_in_database_is_refused(tmp_path):
    _usb(tmp_path, "3-1", "3277", "00b2")
    with pytest.raises(actions.ActionError):
        actions.set_camera(False, str(tmp_path), [MOUSE])
    assert (tmp_path / "3-1" / "authorized").read_text().strip() == "1"


def test_port_name_check():
    assert actions.PORT_RE.match("3-1") and actions.PORT_RE.match("1-2.4.1")
    assert not actions.PORT_RE.match("../etc") and not actions.PORT_RE.match("3-1/../x")


# ---------- dispatcher (request handling and permissions) ----------

class Recorder:
    def __init__(self, allow=True):
        self.allow = allow
        self.calls = []
        self.interactive = []

    def __call__(self, action_id, pid, uid, interactive=True):
        self.calls.append((action_id, pid, uid))
        self.interactive.append(interactive)
        return (self.allow, "" if self.allow else "Действие не подтверждено.")


@pytest.fixture
def fake_actions(monkeypatch):
    done = []
    monkeypatch.setattr(actions, "set_power_profile", lambda v: done.append(("profile", v)) or {"profile": v})
    monkeypatch.setattr(actions, "set_camera", lambda v: done.append(("camera", v)) or {"cameras": []})
    return done


def _send(dispatcher, payload, pid=123, uid=1000):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return dispatcher.handle(raw, pid, uid)


def test_ping_needs_no_authorization(fake_actions):
    auth = Recorder()
    d = server.Dispatcher(auth, log=lambda t: None)
    assert _send(d, {"action": "ping"}) == {"ok": True, "result": {"pong": True}}
    assert auth.calls == []


def test_change_needs_authorization(fake_actions):
    auth = Recorder(allow=True)
    d = server.Dispatcher(auth, log=lambda t: None)
    r = _send(d, {"action": "set_power_profile", "value": "performance"}, pid=77, uid=1000)
    assert r["ok"] is True
    assert auth.calls == [("org.dockit.set-power-profile", 77, 1000)]
    assert fake_actions == [("profile", "performance")]


def test_refused_by_polkit_changes_nothing(fake_actions):
    d = server.Dispatcher(Recorder(allow=False), log=lambda t: None)
    r = _send(d, {"action": "set_camera", "value": False})
    assert r["ok"] is False
    assert fake_actions == []


def test_root_caller_skips_polkit(fake_actions):
    auth = Recorder(allow=False)
    d = server.Dispatcher(auth, log=lambda t: None)
    assert _send(d, {"action": "set_camera", "value": True}, uid=0)["ok"] is True
    assert auth.calls == []


def test_requests_are_interactive_by_default(fake_actions):
    auth = Recorder()
    d = server.Dispatcher(auth, log=lambda t: None)
    _send(d, {"action": "set_power_profile", "value": "performance"})
    assert auth.interactive == [True]


def test_background_request_is_passed_as_quiet(fake_actions):
    auth = Recorder()
    d = server.Dispatcher(auth, log=lambda t: None)
    _send(d, {"action": "set_camera", "value": False, "interactive": False})
    assert auth.interactive == [False]


@pytest.mark.parametrize("bad", ["no", 0, None, [], {}])
def test_interactive_must_be_bool(fake_actions, bad):
    auth = Recorder()
    d = server.Dispatcher(auth, log=lambda t: None)
    r = _send(d, {"action": "set_camera", "value": False, "interactive": bad})
    assert r["ok"] is False and auth.calls == [] and fake_actions == []


class _Proc:
    def __init__(self, returncode):
        self.returncode = returncode


def test_quiet_pkcheck_never_allows_user_interaction(monkeypatch):
    seen = []

    def run(cmd, **kw):
        seen.append(cmd)
        return _Proc(2)  # polkit: authentication would be needed

    monkeypatch.setattr(server.subprocess, "run", run)
    allowed, message = server.polkit_authorizer("org.dockit.set-camera", os.getpid(), os.getuid(), False)
    assert allowed is False and message == server.QUIET_REFUSED
    assert "--allow-user-interaction" not in seen[0]
    server.polkit_authorizer("org.dockit.set-camera", os.getpid(), os.getuid(), True)
    assert "--allow-user-interaction" in seen[1]


def test_power_profile_needs_no_password_but_camera_does():
    policy = (Path(__file__).resolve().parents[1] / "data/polkit/org.dockit.policy").read_text()
    blocks = dict(re.findall(r'<action id="([^"]+)">(.*?)</action>', policy, re.S))
    assert "<allow_active>yes</allow_active>" in blocks["org.dockit.set-power-profile"]
    assert "<allow_active>yes</allow_active>" in blocks["org.dockit.set-kbd-backlight"]
    assert "<allow_any>no</allow_any>" in blocks["org.dockit.set-kbd-backlight"]
    assert "<allow_inactive>no</allow_inactive>" in blocks["org.dockit.set-kbd-backlight"]
    for action_id in ("org.dockit.set-camera", "org.dockit.set-cpu", "org.dockit.set-gpu-limit"):
        assert "<allow_active>auth_self_keep</allow_active>" in blocks[action_id]
        assert "<allow_any>no</allow_any>" in blocks[action_id]


@pytest.mark.parametrize("payload", [
    {"action": "run", "cmd": "id"},
    {"action": "../set_camera"},
    {"action": 5},
    {"value": "x"},
    ["set_camera"],
    "set_camera",
])
def test_unknown_or_malformed_requests(fake_actions, payload):
    d = server.Dispatcher(Recorder(), log=lambda t: None)
    assert _send(d, payload)["ok"] is False
    assert fake_actions == []


def test_garbage_and_oversize(fake_actions):
    d = server.Dispatcher(Recorder(), log=lambda t: None)
    assert _send(d, b"not json")["ok"] is False
    assert _send(d, b"\xff\xfe")["ok"] is False
    big = b'{"action":"ping","pad":"' + b"a" * (MAX_MESSAGE + 10) + b'"}'
    assert _send(d, big)["ok"] is False


def test_action_error_is_returned_not_raised(monkeypatch):
    def boom(_):
        raise actions.ActionError("Недопустимый режим.")

    monkeypatch.setattr(actions, "set_power_profile", boom)
    d = server.Dispatcher(Recorder(), log=lambda t: None)
    r = _send(d, {"action": "set_power_profile", "value": "x"})
    assert r == {"ok": False, "error": "Недопустимый режим."}


def test_unexpected_crash_does_not_leak_details(monkeypatch):
    def boom(_):
        raise RuntimeError("secret path /root/x")

    monkeypatch.setattr(actions, "set_power_profile", boom)
    d = server.Dispatcher(Recorder(), log=lambda t: None)
    r = _send(d, {"action": "set_power_profile", "value": "x"})
    assert r["ok"] is False and "secret" not in r["error"]


# ---------- helpers ----------

def test_process_start_time_of_this_process():
    start = server.process_start_time(os.getpid())
    assert start is not None and start.isdigit()
    assert server.process_start_time(2**30) is None


def test_polkit_missing_means_refused(monkeypatch):
    def missing(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(server.subprocess, "run", missing)
    allowed, message = server.polkit_authorizer("org.dockit.set-camera", os.getpid(), os.getuid())
    assert allowed is False and "polkit" in message


# ---------- real socket, end to end ----------

@pytest.fixture
def running_server(fake_actions):
    directory = tempfile.mkdtemp(prefix="dockit-test-")
    path = os.path.join(directory, "s.sock")
    auth = Recorder(allow=True)
    dispatcher = server.Dispatcher(auth, log=lambda t: None)
    seen = []  # (pid, uid) the service read from the socket for each request
    original = dispatcher.handle

    def spy(raw, pid, uid):
        seen.append((pid, uid))
        return original(raw, pid, uid)

    dispatcher.handle = spy
    srv = server.Server(path, dispatcher)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    auth.seen = seen
    yield path, auth
    srv.shutdown()
    srv.server_close()
    for f in Path(directory).glob("*"):
        f.unlink()
    os.rmdir(directory)


def test_socket_round_trip_and_peer_credentials(running_server, fake_actions):
    path, auth = running_server
    assert daemon_running(path) is True
    response = request({"action": "set_camera", "value": False}, path, timeout=5)
    assert response["ok"] is True
    # the service read the real pid and uid of this process from the socket,
    # it does not trust anything the client writes in the message
    assert auth.seen[-1] == (os.getpid(), os.getuid())
    assert fake_actions == [("camera", False)]
    if os.getuid() != 0:  # root skips polkit by design
        assert auth.calls == [("org.dockit.set-camera", os.getpid(), os.getuid())]


def test_socket_refuses_unknown_action(running_server, fake_actions):
    path, _ = running_server
    assert request({"action": "format_disk"}, path, timeout=5)["ok"] is False
    assert fake_actions == []


def test_client_without_service(tmp_path):
    missing = str(tmp_path / "none.sock")
    assert daemon_running(missing) is False
    with pytest.raises(DaemonUnavailable):
        request({"action": "ping"}, missing, timeout=1)
