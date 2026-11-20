"""Is the NVIDIA card asleep, and which programs keep it open?

Everything here only reads /sys and /proc and never starts nvidia-smi:
asking the driver through nvidia-smi wakes a sleeping card, which costs
battery. Use gpu_asleep() before calling nvidia-smi.
"""

from __future__ import annotations

import glob
import os
import re

from . import sysfs

PCI = "/sys/bus/pci/devices"
PROC = "/proc"
NVIDIA_VENDOR = "0x10de"

# /dev/nvidia0, /dev/nvidiactl, /dev/nvidia-modeset, /dev/nvidia-uvm, /dev/nvidia-uvm-tools
NODE_RE = re.compile(r"^/dev/nvidia([0-9]+|ctl|-modeset|-uvm(-tools)?)$")
# /dev/nvidia0 is the card itself: a program holding it usually keeps the card awake
CARD_RE = re.compile(r"^/dev/nvidia[0-9]+$")


def nvidia_gpus(base: str = PCI) -> list[str]:
    """sysfs folders of NVIDIA display devices (class 0x03xxxx)."""
    found = []
    for dev in sorted(glob.glob(f"{base}/*")):
        if sysfs.read_text(f"{dev}/vendor") == NVIDIA_VENDOR and \
                (sysfs.read_text(f"{dev}/class") or "").startswith("0x03"):
            found.append(dev)
    return found


def power_state(dev: str) -> dict:
    """{"runtime": "active"|"suspended"|..., "control": "auto"|"on"} (None when unknown).

    control "auto" means the kernel may put the card to sleep; "on" keeps it powered.
    """
    return {
        "runtime": sysfs.read_text(f"{dev}/power/runtime_status"),
        "control": sysfs.read_text(f"{dev}/power/control"),
    }


def gpu_asleep(base: str = PCI) -> bool:
    """True when every NVIDIA card is suspended (then nvidia-smi must not be called)."""
    gpus = nvidia_gpus(base)
    return bool(gpus) and all(power_state(g)["runtime"] == "suspended" for g in gpus)


def is_nvidia_node(target: str) -> bool:
    return bool(NODE_RE.match(target))


def gpu_users(proc: str = PROC) -> list[dict]:
    """Programs with an NVIDIA device file open: [{"pid", "name", "card"}].

    "card" is True when the program holds the card itself (/dev/nvidiaN), not only the
    control files. Only processes we may read are listed (the user's own programs), which
    is exactly what the user can close. Sorted: card holders first, then by name.
    """
    users = []
    for pid_dir in glob.glob(f"{proc}/[0-9]*"):
        nodes = set()
        try:
            for fd in os.listdir(f"{pid_dir}/fd"):
                try:
                    target = os.readlink(f"{pid_dir}/fd/{fd}")
                except OSError:
                    continue
                if is_nvidia_node(target):
                    nodes.add(target)
        except OSError:  # not ours, or the process has ended
            continue
        if not nodes:
            continue
        name = sysfs.read_text(f"{pid_dir}/comm") or "?"
        users.append({"pid": int(os.path.basename(pid_dir)), "name": name,
                      "card": any(CARD_RE.match(n) for n in nodes)})
    users.sort(key=lambda u: (not u["card"], u["name"].lower(), u["pid"]))
    return users


def summary(base: str = PCI, proc: str = PROC) -> dict | None:
    """Everything the window needs, or None when there is no NVIDIA card."""
    gpus = nvidia_gpus(base)
    if not gpus:
        return None
    state = power_state(gpus[0])
    return {
        "runtime": state["runtime"],
        "control": state["control"],
        "asleep": state["runtime"] == "suspended",
        "users": gpu_users(proc),
    }
