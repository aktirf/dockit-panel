#!/usr/bin/env bash
# Removes everything that scripts/install-dev.sh installed.  Run:  sudo scripts/uninstall-dev.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this with sudo:  sudo scripts/uninstall-dev.sh"
    exit 1
fi

systemctl disable --now dockit.service 2>/dev/null || true
rm -f /etc/systemd/system/dockit.service
systemctl daemon-reload
rm -f /usr/share/polkit-1/actions/org.dockit.policy
rm -f /usr/local/bin/dockit-root
rm -rf /opt/dockit /usr/share/dockit /run/dockit
echo "DOCKIT service removed."
