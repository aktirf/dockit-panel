"""All features. To add a feature: create a file here and add it to ALL_MODULES."""

from .battery import Battery
from .battery_limit import BatteryLimit
from .gpu_nvidia import GpuNvidia
from .power_profile import PowerProfile
from .sensors import Sensors
from .wireless import Wireless

ALL_MODULES = [
    PowerProfile,
    Sensors,
    GpuNvidia,
    Battery,
    BatteryLimit,
    Wireless,
]
