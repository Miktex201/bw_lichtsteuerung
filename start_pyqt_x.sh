#!/bin/sh
set -eu

APP_DIR="$(cd "$(dirname "$0")" && pwd)"

export LICHT_DMX_ENABLED="${LICHT_DMX_ENABLED:-1}"
export LICHT_DMX_DEVICE="${LICHT_DMX_DEVICE:-/dev/ttyUSB1}"
export LICHT_DMX_FPS="${LICHT_DMX_FPS:-44}"
export LOGO_GPIO_ENABLED="${LOGO_GPIO_ENABLED:-1}"
export LOGO_GPIO_RED="${LOGO_GPIO_RED:-18}"
export LOGO_GPIO_GREEN="${LOGO_GPIO_GREEN:-10}"
export LOGO_GPIO_BLUE="${LOGO_GPIO_BLUE:-17}"

exec startx /usr/bin/python3 "$APP_DIR/pyqt_app.py" --fullscreen -- :0 vt2 -nocursor
