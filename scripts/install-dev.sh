#!/usr/bin/env bash
# Installs DOCKIT and its background service on this computer (for testing).
# Run from the project folder:  sudo scripts/install-dev.sh
#
# What it does:
#   1. copies the program into /opt/dockit (owned by root, so nobody else can edit
#      code that runs as root);
#   2. puts the device database into /usr/share/dockit/devices;
#   3. installs the polkit rules (the password dialog) and the systemd service;
#   4. starts the service.
# Undo everything with:  sudo scripts/uninstall-dev.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this with sudo:  sudo scripts/install-dev.sh"
    exit 1
fi

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"

echo "[1/4] Installing the program into /opt/dockit ..."
mkdir -p /opt/dockit
# --system-site-packages lets the window use the system PySide6 (the service itself does not need it)
"$PY" -m venv --system-site-packages /opt/dockit/venv
/opt/dockit/venv/bin/pip install --quiet --upgrade "$REPO"
ln -sf /opt/dockit/venv/bin/dockit /usr/local/bin/dockit-root
ln -sf /opt/dockit/venv/bin/dockit /usr/local/bin/dockit
install -Dm644 "$REPO/data/applications/dockit.desktop" /usr/share/applications/dockit.desktop
install -Dm644 "$REPO/data/icons/dockit.svg" /usr/share/icons/hicolor/scalable/apps/dockit.svg

echo "[2/4] Copying the device database ..."
rm -rf /usr/share/dockit/devices
mkdir -p /usr/share/dockit
cp -r "$REPO/devices" /usr/share/dockit/devices

echo "[3/4] Installing polkit rules and the service ..."
install -Dm644 "$REPO/data/polkit/org.dockit.policy" /usr/share/polkit-1/actions/org.dockit.policy
sed 's|^ExecStart=.*|ExecStart=/opt/dockit/venv/bin/dockit daemon|' \
    "$REPO/data/systemd/dockit.service" > /etc/systemd/system/dockit.service
chmod 644 /etc/systemd/system/dockit.service

echo "[4/4] Starting the service ..."
systemctl daemon-reload
systemctl enable --now dockit.service
sleep 1
systemctl --no-pager --lines=5 status dockit.service || true

echo
echo "Done. Try:  dockit scan    dockit gui   (or find DOCKIT in the application menu)"
