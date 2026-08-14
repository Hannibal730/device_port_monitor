#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
OUTPUT=${1:-"$PROJECT_DIR/.build/device-port-monitor-monitor"}

mkdir -p "$(dirname -- "$OUTPUT")"

gcc \
    -std=c11 \
    -Os \
    -Wall \
    -Wextra \
    -Werror \
    -ffunction-sections \
    -fdata-sections \
    "$PROJECT_DIR/src/device-port-monitor-monitor.c" \
    -o "$OUTPUT" \
    $(pkg-config --cflags --libs gio-2.0) \
    -Wl,--as-needed \
    -Wl,--gc-sections \
    -Wl,-z,relro \
    -Wl,-z,now \
    -Wl,-s \
    -l:libayatana-appindicator3.so.1 \
    -l:libgtk-3.so.0

printf '%s\n' "$OUTPUT"
