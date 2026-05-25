#!/bin/sh
set -eu

APP_DIR="$(cd "$(dirname "$0")" && pwd)"

exec sudo openvt -c 2 -f -s -- su - "$USER" -c "cd '$APP_DIR' && ./start_pyqt_x.sh"
