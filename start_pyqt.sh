#!/bin/sh
set -eu

cd "$(dirname "$0")"

export LICHT_DMX_ENABLED="${LICHT_DMX_ENABLED:-1}"
export LICHT_DMX_DEVICE="${LICHT_DMX_DEVICE:-/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BG00QFIM-if00-port0}"
export LICHT_DMX_FPS="${LICHT_DMX_FPS:-44}"
export LOGO_GPIO_ENABLED="${LOGO_GPIO_ENABLED:-1}"
export LOGO_GPIO_RED="${LOGO_GPIO_RED:-18}"
export LOGO_GPIO_GREEN="${LOGO_GPIO_GREEN:-10}"
export LOGO_GPIO_BLUE="${LOGO_GPIO_BLUE:-17}"
export PYQT_API_BASE="${PYQT_API_BASE:-http://127.0.0.1:8080}"

if [ -S /tmp/.X11-unix/X0 ]; then
    export DISPLAY="${DISPLAY:-:0}"
    if [ -z "${XAUTHORITY:-}" ] && [ -f "$HOME/.Xauthority" ]; then
        export XAUTHORITY="$HOME/.Xauthority"
    fi
else
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-linuxfb}"
fi

PYQT_ARGS="--fullscreen"
if [ "${PYQT_USE_WEBSERVER:-0}" = "1" ]; then
    PYQT_ARGS="$PYQT_ARGS --use-webserver --api-base $PYQT_API_BASE"
fi

exec /usr/bin/python3 pyqt_app.py $PYQT_ARGS
