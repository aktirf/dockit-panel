#!/usr/bin/env bash
# Collects information about the keyboard backlight, fans and the mouse into one text file,
# so that support for them can be worked out. It only READS; it changes nothing.
# Run:  scripts/probe.sh      then send ~/dockit-probe.txt to the developer.
OUT="$HOME/dockit-probe.txt"
{
echo "== DOCKIT probe $(date -Is)"
echo "== kernel";            uname -r
echo "== laptop";            cat /sys/class/dmi/id/product_name /sys/class/dmi/id/bios_version 2>/dev/null
echo "== USB devices";       lsusb 2>&1
echo "== keyboard 0414:8104 (serial numbers removed)"
lsusb -v -d 0414:8104 2>&1 | grep -vi "iSerial" | head -80
echo "== LEDs";              ls /sys/class/leds 2>&1
echo "== backlight";         ls /sys/class/backlight 2>&1
echo "== hwmon chips and fans"
for h in /sys/class/hwmon/hwmon*; do
  echo "$h: $(cat "$h/name" 2>/dev/null) | $(ls "$h" 2>/dev/null | grep -E '^(fan|pwm)' | tr '\n' ' ')"
done
echo "== WMI devices";       ls /sys/bus/wmi/devices 2>&1
echo "== ACPI platform";     ls /sys/firmware/acpi 2>&1; cat /sys/firmware/acpi/platform_profile_choices 2>&1
echo "== kernel modules";    lsmod | grep -i -E 'gigabyte|wmi|ec_|ite|hid|nvidia_wmi' 2>&1
echo "== hidraw";            ls -l /dev/hidraw* 2>&1
echo "== HID power supplies"; ls /sys/class/power_supply 2>&1
echo "== NVIDIA";            nvidia-smi -q -d POWER,PERFORMANCE 2>&1 | head -60
echo "== bluetooth";         bluetoothctl devices 2>&1
echo "== CPU tuning";        cat /sys/devices/system/cpu/cpufreq/boost /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_available_preferences 2>&1
} > "$OUT" 2>&1
echo "Done. File: $OUT (check it quickly, then send it to the developer)."
