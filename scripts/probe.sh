#!/usr/bin/env bash
# Universal read-only hardware probe for DOCKIT (works on any Linux laptop or PC).
# Collects safe technical info (no serial numbers, no passwords, no usernames) into
# ~/dockit-probe.txt so new laptop features can be supported cleanly.
# Run:  scripts/probe.sh
set -u

OUT="$HOME/dockit-probe.txt"
{
echo "== DOCKIT universal probe $(date -Is)"
echo "== kernel & OS"
uname -rm
grep -E '^(NAME|PRETTY_NAME|VERSION_ID)=' /etc/os-release 2>/dev/null || true

echo "== hardware identity (no serials)"
printf 'vendor:  %s\n' "$(cat /sys/class/dmi/id/sys_vendor 2>/dev/null || echo unknown)"
printf 'model:   %s\n' "$(cat /sys/class/dmi/id/product_name 2>/dev/null || echo unknown)"
printf 'chassis: %s\n' "$(cat /sys/class/dmi/id/chassis_type 2>/dev/null || echo unknown)"
printf 'bios:    %s\n' "$(cat /sys/class/dmi/id/bios_version 2>/dev/null || echo unknown)"

echo "== desktop & display"
printf 'XDG_CURRENT_DESKTOP=%s  WAYLAND_DISPLAY=%s  DISPLAY=%s\n' \
  "${XDG_CURRENT_DESKTOP:-}" "${WAYLAND_DISPLAY:-}" "${DISPLAY:-}"

echo "== CPU & tuning"
grep -m1 '^model name' /proc/cpuinfo 2>/dev/null || true
printf 'driver:  %s\n' "$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver 2>/dev/null || echo none)"
printf 'gov:     %s\n' "$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo none)"
printf 'boost:   %s\n' "$(cat /sys/devices/system/cpu/cpufreq/boost 2>/dev/null || echo none)"
printf 'epp:     %s\n' "$(cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference 2>/dev/null || echo none)"
printf 'epp_all: %s\n' "$(cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_available_preferences 2>/dev/null || echo none)"

echo "== ACPI platform profiles & services"
printf 'profile: %s\n' "$(cat /sys/firmware/acpi/platform_profile 2>/dev/null || echo none)"
printf 'choices: %s\n' "$(cat /sys/firmware/acpi/platform_profile_choices 2>/dev/null || echo none)"
command -v powerprofilesctl >/dev/null && powerprofilesctl list 2>&1 || echo "powerprofilesctl: not installed"
command -v swayidle >/dev/null && echo "swayidle: installed" || echo "swayidle: not installed"

echo "== battery & charge limits"
for ps in /sys/class/power_supply/*; do
  [ -d "$ps" ] || continue
  printf '%s: type=%s status=%s cap=%s end_thresh=%s\n' \
    "$(basename "$ps")" \
    "$(cat "$ps/type" 2>/dev/null || echo ?)" \
    "$(cat "$ps/status" 2>/dev/null || echo ?)" \
    "$(cat "$ps/capacity" 2>/dev/null || echo ?)" \
    "$(cat "$ps/charge_control_end_threshold" 2>/dev/null || echo -)"
done
for cm in /sys/bus/platform/drivers/ideapad_acpi/VPC2004:*/conservation_mode; do
  [ -f "$cm" ] && printf 'ideapad conservation_mode: %s\n' "$(cat "$cm" 2>/dev/null)"
done

echo "== GPUs (without waking sleeping NVIDIA)"
for dev in /sys/bus/pci/devices/*; do
  cls="$(cat "$dev/class" 2>/dev/null || true)"
  case "$cls" in 0x03*) ;; *) continue ;; esac
  ven="$(cat "$dev/vendor" 2>/dev/null || echo ?)"
  did="$(cat "$dev/device" 2>/dev/null || echo ?)"
  rt="$(cat "$dev/power/runtime_status" 2>/dev/null || echo ?)"
  ctrl="$(cat "$dev/power/control" 2>/dev/null || echo ?)"
  printf '%s: vendor=%s device=%s runtime=%s control=%s\n' "$(basename "$dev")" "$ven" "$did" "$rt" "$ctrl"
done
nv_awake=0
for dev in /sys/bus/pci/devices/*; do
  [ "$(cat "$dev/vendor" 2>/dev/null || true)" = "0x10de" ] || continue
  case "$(cat "$dev/class" 2>/dev/null || true)" in 0x03*) ;; *) continue ;; esac
  [ "$(cat "$dev/power/runtime_status" 2>/dev/null || true)" != "suspended" ] && nv_awake=1
done
if [ "$nv_awake" -eq 1 ] && command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,driver_version,power.limit,power.min_limit,power.max_limit --format=csv 2>&1
elif [ "$nv_awake" -eq 0 ]; then
  echo "nvidia-smi: skipped (no awake NVIDIA card)"
fi

echo "== hwmon chips & fans"
for h in /sys/class/hwmon/hwmon*; do
  [ -d "$h" ] || continue
  echo "$(basename "$h"): $(cat "$h/name" 2>/dev/null) | $(ls "$h" 2>/dev/null | grep -E '^(temp[0-9]+_input|fan[0-9]+_input|pwm[0-9]+)$' | tr '\n' ' ')"
done

echo "== backlight & LEDs"
ls /sys/class/backlight 2>&1 || true
ls /sys/class/leds 2>&1 || true

echo "== USB devices & UVC cameras"
command -v lsusb >/dev/null && lsusb 2>&1 || true
for d in /sys/bus/usb/devices/*:*; do
  [ "$(cat "$d/bInterfaceClass" 2>/dev/null || true)" = "0e" ] && echo "UVC interface: $(basename "$d")"
done

echo "== HID LampArray / hidraw"
ls /sys/class/hidraw 2>&1 || true

echo "== laptop kernel modules"
lsmod 2>/dev/null | grep -i -E 'thinkpad|ideapad|legion|asus|rog|msi|acer|dell|hp_wmi|gigabyte|samsung|lg_laptop|system76|framework|ec_sys|acpi_ec|ite|nvidia_wmi|amdgpu|intel_pstate|amd_pstate' || true

echo "== WMI devices"
ls /sys/bus/wmi/devices 2>&1 || true
} > "$OUT" 2>&1
echo "Done. File saved to: $OUT (review briefly, then attach to a GitHub issue)."
