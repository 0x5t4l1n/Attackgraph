#!/usr/bin/env bash
# AttackGraph desktop launcher
# Starts the Tauri desktop application
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINARY="$SCRIPT_DIR/frontend/src-tauri/target/release/attackgraph"
APPIMAGE="$SCRIPT_DIR/frontend/src-tauri/target/release/bundle/appimage/AttackGraph_0.1.0_amd64.AppImage"

if [ -f "$APPIMAGE" ]; then
    exec "$APPIMAGE" "$@"
elif [ -f "$BINARY" ]; then
    exec "$BINARY" "$@"
else
    echo "AttackGraph binary not found. Build first with: cd frontend && cargo tauri build"
    exit 1
fi
