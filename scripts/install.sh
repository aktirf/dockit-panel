#!/usr/bin/env bash
# One-step install of DOCKIT with everything it needs (Arch, EndeavourOS and Arch-based systems).
# Run from the project folder as your normal user (it asks for your password when needed):
#     scripts/install.sh
# Undo with:  sudo scripts/uninstall-dev.sh
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
    echo "Run this as your normal user, not as root:  scripts/install.sh"
    exit 1
fi

REPO="$(cd "$(dirname "$0")/.." && pwd)"

# what DOCKIT uses: window, fonts, idle detection, sound, power, sensors, Wi-Fi and Bluetooth
PACKAGES=(python python-pip pyside6 ttf-ibm-plex swayidle libpulse pipewire-pulse
          polkit upower lm_sensors networkmanager bluez-utils libnotify)

if command -v pacman >/dev/null 2>&1; then
    echo "[1/2] Installing packages DOCKIT needs ..."
    sudo pacman -S --needed "${PACKAGES[@]}"
else
    echo "pacman was not found, so I cannot install packages for you."
    echo "Please install the equivalents of: ${PACKAGES[*]}"
    echo "Then run:  sudo scripts/install-dev.sh"
    exit 1
fi

echo "[2/2] Installing DOCKIT and its service ..."
sudo "$REPO/scripts/install-dev.sh"

echo
echo "All done. Start DOCKIT from the application menu, or run:  dockit gui"
if ! command -v nvidia-smi >/dev/null 2>&1 && lspci 2>/dev/null | grep -qi nvidia; then
    echo "Note: an NVIDIA card was found but its driver is not installed (sudo pacman -S nvidia-open nvidia-utils)."
fi
