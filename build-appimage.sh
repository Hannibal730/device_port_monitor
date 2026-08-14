#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VERSION=1.2.0
MACHINE_ARCH=$(uname -m)

case "$MACHINE_ARCH" in
    x86_64)
        APPIMAGE_ARCH=x86_64
        ;;
    aarch64|arm64)
        APPIMAGE_ARCH=aarch64
        ;;
    *)
        printf 'Unsupported architecture: %s\n' "$MACHINE_ARCH" >&2
        exit 1
        ;;
esac

APPDIR="$PROJECT_DIR/.build/DevicePortMonitor.AppDir"
DIST_DIR="$PROJECT_DIR/dist"
TOOLS_DIR="$PROJECT_DIR/.tools"
APPIMAGETOOL=${APPIMAGETOOL:-"$TOOLS_DIR/appimagetool-$APPIMAGE_ARCH.AppImage"}
OUTPUT="$DIST_DIR/Device_Port_Monitor-$VERSION-$APPIMAGE_ARCH.AppImage"

if [ ! -x "$APPIMAGETOOL" ]; then
    mkdir -p "$TOOLS_DIR"
    URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$APPIMAGE_ARCH.AppImage"
    printf 'Downloading appimagetool from %s\n' "$URL"
    curl --fail --location --output "$APPIMAGETOOL" "$URL"
    chmod 0755 "$APPIMAGETOOL"
fi

rm -rf "$APPDIR"
mkdir -p \
    "$APPDIR/usr/bin" \
    "$APPDIR/usr/share/applications" \
    "$APPDIR/usr/share/doc/device-port-monitor" \
    "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
    "$DIST_DIR"

install -m 0755 "$PROJECT_DIR/packaging/AppRun" "$APPDIR/AppRun"
install -m 0755 "$PROJECT_DIR/device-port-monitor" \
    "$APPDIR/usr/bin/device-port-monitor"
"$PROJECT_DIR/build-monitor.sh" \
    "$APPDIR/usr/bin/device-port-monitor-monitor"
install -m 0644 "$PROJECT_DIR/device-port-monitor.desktop" \
    "$APPDIR/device-port-monitor.desktop"
install -m 0644 "$PROJECT_DIR/device-port-monitor.desktop" \
    "$APPDIR/usr/share/applications/device-port-monitor.desktop"
install -m 0644 "$PROJECT_DIR/device-port-monitor.png" \
    "$APPDIR/device-port-monitor.png"
install -m 0644 "$PROJECT_DIR/device-port-monitor.png" \
    "$APPDIR/usr/share/icons/hicolor/256x256/apps/device-port-monitor.png"
install -m 0644 "$PROJECT_DIR/LICENSE" \
    "$APPDIR/usr/share/doc/device-port-monitor/LICENSE"
install -m 0644 "$PROJECT_DIR/README.md" \
    "$APPDIR/usr/share/doc/device-port-monitor/README.md"
ln -s device-port-monitor.png "$APPDIR/.DirIcon"

rm -f "$OUTPUT"
ARCH="$APPIMAGE_ARCH" VERSION="$VERSION" APPIMAGE_EXTRACT_AND_RUN=1 \
    "$APPIMAGETOOL" --no-appstream "$APPDIR" "$OUTPUT"
chmod 0755 "$OUTPUT"
printf '%s\n' "$OUTPUT"
