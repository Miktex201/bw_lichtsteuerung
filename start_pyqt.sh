#!/bin/sh
set -eu

cd "$(dirname "$0")"

export LICHT_DMX_ENABLED="${LICHT_DMX_ENABLED:-1}"
export LICHT_DMX_DEVICE="${LICHT_DMX_DEVICE:-/dev/ttyUSB1}"
export LICHT_DMX_FPS="${LICHT_DMX_FPS:-44}"
export LOGO_GPIO_ENABLED="${LOGO_GPIO_ENABLED:-1}"
export LOGO_GPIO_RED="${LOGO_GPIO_RED:-18}"
export LOGO_GPIO_GREEN="${LOGO_GPIO_GREEN:-10}"
export LOGO_GPIO_BLUE="${LOGO_GPIO_BLUE:-17}"

if [ -S /tmp/.X11-unix/X0 ]; then
    export DISPLAY="${DISPLAY:-:0}"
    if [ -z "${XAUTHORITY:-}" ] && [ -f "$HOME/.Xauthority" ]; then
        export XAUTHORITY="$HOME/.Xauthority"
    fi
else
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-linuxfb}"
fi

exec /usr/bin/python3 pyqt_app.py --fullscreen
