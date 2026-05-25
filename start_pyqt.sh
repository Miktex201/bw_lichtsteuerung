#!/bin/sh
set -eu

cd "$(dirname "$0")"

export LICHT_DMX_ENABLED="${LICHT_DMX_ENABLED:-1}"
export LICHT_DMX_DEVICE="${LICHT_DMX_DEVICE:-/dev/ttyUSB0}"
export LICHT_DMX_FPS="${LICHT_DMX_FPS:-44}"
export DISPLAY="${DISPLAY:-:0}"

if [ -z "${XAUTHORITY:-}" ] && [ -f "$HOME/.Xauthority" ]; then
    export XAUTHORITY="$HOME/.Xauthority"
fi

exec python3 pyqt_app.py --fullscreen
