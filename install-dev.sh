#!/usr/bin/env bash
# install-dev.sh - Installs the Development version of Whisp to your system launcher

# Ensure we're in the right directory
cd "$(dirname "$0")"

APP_DIR=$(pwd)
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

echo "Installing Whisp (Development)..."

# Create directories if they don't exist
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

# Copy the development icon
if [ -f "data/icons/io.github.tanaybhomia.Whisp.Devel.svg" ]; then
    cp "data/icons/io.github.tanaybhomia.Whisp.Devel.svg" "$ICON_DIR/"
    echo "Copied development icon."
else
    echo "WARNING: Could not find data/icons/io.github.tanaybhomia.Whisp.Devel.svg"
fi

# Generate the .desktop file
cat <<EOF > "$DESKTOP_DIR/io.github.tanaybhomia.Whisp.Devel.desktop"
[Desktop Entry]
Name=Whisp (Development)
Comment=A minimalist, gesture-driven scratchpad for GNOME.
Exec=$APP_DIR/run.sh --dev
Icon=io.github.tanaybhomia.Whisp.Devel
Terminal=false
Type=Application
Categories=Utility;TextEditor;
StartupNotify=true
EOF

echo "Created launcher entry at $DESKTOP_DIR/io.github.tanaybhomia.Whisp.Devel.desktop"

# Refresh GNOME databases
update-desktop-database "$DESKTOP_DIR" 2>/dev/null
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null

echo ""
echo "Done! You can now search for 'Whisp' in your app launcher."
echo "You will see two icons. The one with the dev icon will run your local codebase directly."
