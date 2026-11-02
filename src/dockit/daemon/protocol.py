"""Shared constants for the service and its clients.

Messages are one line of JSON in each direction:
    request:  {"action": "set_power_profile", "value": "performance"}
    response: {"ok": true, "result": {...}}   or   {"ok": false, "error": "text"}
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
}
