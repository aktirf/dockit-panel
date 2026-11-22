"""Shared constants for the service and its clients.

Messages are one line of JSON in each direction:
    request:  {"action": "set_power_profile", "value": "performance"}
    response: {"ok": true, "result": {...}}   or   {"ok": false, "error": "text"}

Optional request field "interactive" (bool, default true): false means "never show a
password dialog" and is sent by automatic profile switching. Actions that the polkit
policy allows without a password still work; the rest are refused quietly.
"""

SOCKET_PATH = "/run/dockit/dockit.sock"
MAX_MESSAGE = 4096  # bytes; longer requests are rejected

# action name -> polkit action id (None = needs no authorization, changes nothing)
POLKIT_IDS = {
    "ping": None,
    "set_power_profile": "org.dockit.set-power-profile",
    "set_camera": "org.dockit.set-camera",
    "set_brightness": "org.dockit.set-brightness",
    "set_boost": "org.dockit.set-cpu",
    "set_epp": "org.dockit.set-cpu",
    "set_gpu_power_limit": "org.dockit.set-gpu-limit",
    "set_kbd_backlight": "org.dockit.set-kbd-backlight",
    "set_battery_limit": "org.dockit.set-battery-limit",
}
