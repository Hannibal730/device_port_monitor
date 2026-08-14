#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
VERSION=1.2.0
DEB_ARCH=$(dpkg --print-architecture)
PACKAGE_NAME=device-port-monitor_${VERSION}_${DEB_ARCH}.deb
BUILD_DIR="$PROJECT_DIR/.build/device-port-monitor"
DIST_DIR="$PROJECT_DIR/dist"

rm -rf "$PROJECT_DIR/.build"
mkdir -p \
    "$BUILD_DIR/DEBIAN" \
    "$BUILD_DIR/usr/bin" \
    "$BUILD_DIR/usr/lib/device-port-monitor" \
    "$BUILD_DIR/usr/lib/systemd/user" \
    "$BUILD_DIR/usr/share/applications" \
    "$BUILD_DIR/usr/share/pixmaps" \
    "$BUILD_DIR/usr/share/doc/device-port-monitor" \
    "$DIST_DIR"

install -m 0755 "$PROJECT_DIR/src/device-port-monitor.py" \
    "$BUILD_DIR/usr/bin/device-port-monitor"
"$PROJECT_DIR/scripts/build-monitor.sh" \
    "$BUILD_DIR/usr/lib/device-port-monitor/device-port-monitor-monitor"
install -m 0644 "$PROJECT_DIR/packaging/common/device-port-monitor.service" \
    "$BUILD_DIR/usr/lib/systemd/user/device-port-monitor.service"
install -m 0644 "$PROJECT_DIR/packaging/common/device-port-monitor.desktop" \
    "$BUILD_DIR/usr/share/applications/device-port-monitor.desktop"
install -m 0644 "$PROJECT_DIR/assets/device-port-monitor.png" \
    "$BUILD_DIR/usr/share/pixmaps/device-port-monitor.png"
install -m 0644 "$PROJECT_DIR/README.md" \
    "$BUILD_DIR/usr/share/doc/device-port-monitor/README.md"
install -m 0644 "$PROJECT_DIR/LICENSE" \
    "$BUILD_DIR/usr/share/doc/device-port-monitor/copyright"
sed "s/^Architecture:.*/Architecture: $DEB_ARCH/" \
    "$PROJECT_DIR/packaging/deb/DEBIAN/control" > "$BUILD_DIR/DEBIAN/control"
install -m 0755 "$PROJECT_DIR/packaging/deb/DEBIAN/postinst" \
    "$BUILD_DIR/DEBIAN/postinst"
install -m 0755 "$PROJECT_DIR/packaging/deb/DEBIAN/postrm" \
    "$BUILD_DIR/DEBIAN/postrm"

dpkg-deb --root-owner-group --build "$BUILD_DIR" "$DIST_DIR/$PACKAGE_NAME"
printf '%s\n' "$DIST_DIR/$PACKAGE_NAME"
