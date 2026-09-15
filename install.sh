#!/bin/sh
# TOUCHaDESKTOP installer — double-click friendly, no flags needed.
# Installs into ~/.local (no sudo) and adds a start-menu entry that
# opens only the control GUI (no terminal).
#
# Usage:
#   ./install.sh            install / update
#   ./install.sh --uninstall  remove again
set -eu

SRC_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEST_DIR="$HOME/.local/share/TOUCHaDESKTOP"
DESKTOP_FILE="$HOME/.local/share/applications/TOUCHa.desktop"

uninstall() {
  rm -f "$DESKTOP_FILE"
  rm -rf "$DEST_DIR"
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
  fi
  echo "TOUCHaDESKTOP removed."
}

if [ "${1:-}" = "--uninstall" ]; then
  uninstall
  exit 0
fi
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: ./install.sh [--uninstall]"
  exit 0
fi

for f in TOUCHaDESKTOP toucha_gui.pyc toucha_icon.png "TOUCHa.desktop"; do
  if [ ! -f "$SRC_DIR/$f" ]; then
    echo "Missing $f next to install.sh — run from the extracted release folder." >&2
    exit 1
  fi
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found. Please install Python 3 first." >&2
  exit 1
fi
if ! python3 -c "import PyQt6" 2>/dev/null; then
  echo "Python package PyQt6 is required for the GUI but was not found." >&2
  echo "Install it with your package manager, e.g.:" >&2
  echo "  Fedora: sudo dnf install python3-pyqt6" >&2
  echo "  Ubuntu/Debian: sudo apt install python3-pyqt6" >&2
  exit 1
fi
# The GUI ships compiled (toucha_gui.pyc): needs the matching interpreter.
if ! python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 14) else 1)" 2>/dev/null; then
  echo "Python 3.14+ is required for the GUI (older Pythons cannot run it)." >&2
  echo "Alternatively use the Flatpak (bundles everything):" >&2
  echo "  flatpak --user install ./com.toucha.Streamer.flatpak" >&2
  exit 1
fi

mkdir -p "$DEST_DIR"
cp -f "$SRC_DIR/TOUCHaDESKTOP" "$DEST_DIR/TOUCHaDESKTOP"
cp -f "$SRC_DIR/toucha_gui.pyc" "$DEST_DIR/toucha_gui.pyc"
cp -f "$SRC_DIR/toucha_icon.png" "$DEST_DIR/toucha_icon.png"
chmod +x "$DEST_DIR/TOUCHaDESKTOP"

mkdir -p "$HOME/.local/share/applications"
# The shipped template uses %INSTALL_DIR% as placeholder for the real path
# (desktop files require absolute paths).
sed "s|%INSTALL_DIR%|$DEST_DIR|g" "$SRC_DIR/TOUCHa.desktop" > "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"
if command -v desktop-file-validate >/dev/null 2>&1; then
  desktop-file-validate "$DESKTOP_FILE" || echo "Warning: desktop file validation reported an issue." >&2
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

echo "TOUCHaDESKTOP installed."
echo "Open TOUCHaDESKTOP from the start menu and press Start."
