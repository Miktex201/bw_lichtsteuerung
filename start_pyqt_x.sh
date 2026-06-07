#!/bin/sh
set -eu

APP_DIR="$(cd "$(dirname "$0")" && pwd)"

export LICHT_DMX_ENABLED="${LICHT_DMX_ENABLED:-1}"
export LICHT_DMX_DEVICE="${LICHT_DMX_DEVICE:-/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BG00QFIM-if00-port0}"
export LICHT_DMX_FPS="${LICHT_DMX_FPS:-44}"
export LOGO_GPIO_ENABLED="${LOGO_GPIO_ENABLED:-1}"
export LOGO_GPIO_RED="${LOGO_GPIO_RED:-18}"
export LOGO_GPIO_GREEN="${LOGO_GPIO_GREEN:-10}"
export LOGO_GPIO_BLUE="${LOGO_GPIO_BLUE:-17}"
export PYQT_API_BASE="${PYQT_API_BASE:-http://127.0.0.1:8080}"

PYQT_ARGS="--fullscreen"
if [ "${PYQT_USE_WEBSERVER:-0}" = "1" ]; then
    PYQT_ARGS="$PYQT_ARGS --use-webserver --api-base $PYQT_API_BASE"
fi

exec startx /usr/bin/python3 "$APP_DIR/pyqt_app.py" $PYQT_ARGS -- :0 vt2 -nocursor
