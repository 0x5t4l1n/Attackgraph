#!/usr/bin/env bash
# AttackGraph Linux Installer
# Usage: bash install.sh [--appimage | --deb | --local]
set -euo pipefail

PROJ_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPIMAGE="$PROJ_DIR/frontend/src-tauri/target/release/bundle/appimage/AttackGraph_0.1.0_amd64.AppImage"
DEB="$PROJ_DIR/frontend/src-tauri/target/release/bundle/deb/AttackGraph_0.1.0_amd64.deb"
BINARY="$PROJ_DIR/frontend/src-tauri/target/release/attackgraph"

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

MODE="${1:-}"

# ── Verify Python environment ─────────────────────────────────────────────────
check_python() {
    if [ ! -f "$PROJ_DIR/.venv/bin/python3" ]; then
        error "Python virtualenv not found at $PROJ_DIR/.venv"
        info  "Run: cd $PROJ_DIR && python3 -m venv .venv && .venv/bin/pip install -e backend"
        exit 1
    fi
    ok "Python venv found"
}

# ── AppImage ──────────────────────────────────────────────────────────────────
install_appimage() {
    if [ ! -f "$APPIMAGE" ]; then
        error "AppImage not found. Build first: cd frontend && cargo tauri build"
        exit 1
    fi
    DEST="$HOME/.local/bin/AttackGraph.AppImage"
    mkdir -p "$HOME/.local/bin"
    cp "$APPIMAGE" "$DEST"
    chmod +x "$DEST"
    ok "AppImage installed to $DEST"

    # Desktop entry
    DESKTOP_DIR="$HOME/.local/share/applications"
    mkdir -p "$DESKTOP_DIR"
    cat > "$DESKTOP_DIR/attackgraph.desktop" << EOF
[Desktop Entry]
Name=AttackGraph
Comment=Web Application Attack Surface Mapper
Exec=env ATTACKGRAPH_ROOT=$PROJ_DIR $DEST %u
Icon=$PROJ_DIR/frontend/src-tauri/icons/icon.png
Terminal=false
Type=Application
Categories=Security;Network;
Keywords=security;pentest;appsec;scanner;
StartupWMClass=AttackGraph
EOF
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    ok "Desktop entry created"
    info "Launch: $DEST  or search 'AttackGraph' in your app launcher"
}

# ── .deb ──────────────────────────────────────────────────────────────────────
install_deb() {
    if [ ! -f "$DEB" ]; then
        error ".deb not found. Build first: cd frontend && cargo tauri build"
        exit 1
    fi
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y "$DEB"
    elif command -v dpkg &>/dev/null; then
        sudo dpkg -i "$DEB"
        sudo apt-get install -f -y 2>/dev/null || true
    else
        error "apt/dpkg not found. Use --appimage instead."
        exit 1
    fi
    ok ".deb installed"
    info "The app binary is at /usr/bin/attackgraph"
    info "Run with: ATTACKGRAPH_ROOT=$PROJ_DIR attackgraph"
}

# ── Migrate dev database to XDG data dir ─────────────────────────────────────
migrate_db() {
    DATA_DIR="${ATTACKGRAPH_DATA_DIR:-$HOME/.local/share/attackgraph}"
    mkdir -p "$DATA_DIR"
    DEV_DB="$PROJ_DIR/attackgraph.db"
    XDG_DB="$DATA_DIR/attackgraph.db"
    # Only migrate if dev DB has data and XDG DB is empty or smaller
    if [ -f "$DEV_DB" ] && [ "$(stat -c%s "$DEV_DB")" -gt "$(stat -c%s "$XDG_DB" 2>/dev/null || echo 0)" ]; then
        cp "$DEV_DB" "$XDG_DB"
        ok "Database migrated to $XDG_DB"
    fi
    # Migrate AI config
    DEV_AI="$PROJ_DIR/attackgraph_ai_config.json"
    XDG_AI="$DATA_DIR/ai_config.json"
    if [ -f "$DEV_AI" ] && [ ! -f "$XDG_AI" ]; then
        cp "$DEV_AI" "$XDG_AI"
        ok "AI config migrated to $XDG_AI"
    fi
}

# ── Local run (dev) ───────────────────────────────────────────────────────────
run_local() {
    if [ ! -f "$BINARY" ]; then
        error "Binary not found at $BINARY"
        info  "Build first: cd $PROJ_DIR/frontend && cargo tauri build --no-bundle"
        exit 1
    fi
    check_python
    info "Starting AttackGraph (project root: $PROJ_DIR)"
    exec env ATTACKGRAPH_ROOT="$PROJ_DIR" "$BINARY"
}

case "$MODE" in
    --appimage)
        check_python
        migrate_db
        install_appimage
        ;;
    --deb)
        check_python
        migrate_db
        install_deb
        ;;
    --run | --local | "")
        migrate_db
        run_local
        ;;
    --help | -h)
        echo "Usage: bash install.sh [--appimage | --deb | --run]"
        echo "  --appimage  Install the AppImage to ~/.local/bin + desktop entry"
        echo "  --deb       Install the .deb package (Debian/Ubuntu)"
        echo "  --run       Run the binary directly (dev/test)"
        ;;
    *)
        error "Unknown option: $MODE"
        exit 1
        ;;
esac
