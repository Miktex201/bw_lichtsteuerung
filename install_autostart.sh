#!/bin/sh
set -eu

APP_DIR="$(cd "$(dirname "$0")" && pwd)"

sudo install -m 644 "$APP_DIR/systemd/bw-web.service" /etc/systemd/system/bw-web.service
sudo install -m 644 "$APP_DIR/systemd/bw-pyqt.service" /etc/systemd/system/bw-pyqt.service

sudo systemctl daemon-reload
sudo systemctl enable bw-web.service
sudo systemctl enable bw-pyqt.service

echo "Autostart installiert."
echo "Jetzt neu starten mit: sudo reboot"
