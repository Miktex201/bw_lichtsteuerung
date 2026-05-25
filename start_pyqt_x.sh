#!/bin/sh
set -eu

APP_DIR="$(cd "$(dirname "$0")" && pwd)"

export LICHT_DMX_ENABLED="${LICHT_DMX_ENABLED:-1}"
export LICHT_DMX_DEVICE="${LICHT_DMX_DEVICE:-/dev/ttyUSB0}"
export LICHT_DMX_FPS="${LICHT_DMX_FPS:-44}"

exec startx /usr/bin/python3 "$APP_DIR/pyqt_app.py" --fullscreen -- :0 -nocursor
