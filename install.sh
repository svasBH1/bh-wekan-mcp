#!/bin/bash
# Wekan MCP Server - Production Installer
# Run as: bash install.sh
set -e

INSTALL_DIR="/opt/wekan-mcp"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Wekan MCP Server Installer ==="
echo ""

echo "Installing to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

for f in server.py requirements.txt setup_wekan.py; do
    if [ ! -f "$INSTALL_DIR/$f" ] || [ "$SCRIPT_DIR/$f" -nt "$INSTALL_DIR/$f" ]; then
        cp "$SCRIPT_DIR/$f" "$INSTALL_DIR/$f"
    fi
done

if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$INSTALL_DIR/.env"
    echo "Created $INSTALL_DIR/.env — edit it with your credentials."
else
    if grep -q "your_token_here\|your_user_id_here" "$INSTALL_DIR/.env" 2>/dev/null; then
        echo "Warning: $INSTALL_DIR/.env still contains placeholder values."
    fi
fi

echo "Setting up Python environment..."
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
fi

if [ ! -f "$INSTALL_DIR/.requirements_hash" ] || [ "$INSTALL_DIR/requirements.txt" -nt "$INSTALL_DIR/.requirements_hash" ] || ! echo "$(cat "$INSTALL_DIR/requirements.txt")" | sha256sum -c "$INSTALL_DIR/.requirements_hash" 2>/dev/null; then
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    sha256sum "$INSTALL_DIR/requirements.txt" > "$INSTALL_DIR/.requirements_hash"
fi

echo ""
echo "=== Install Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit $INSTALL_DIR/.env with your credentials"
echo "  2. $INSTALL_DIR/venv/bin/python $INSTALL_DIR/setup_wekan.py --validate"
echo ""
echo "Usage: Configure your MCP client to run:"
echo "  $INSTALL_DIR/venv/bin/python $INSTALL_DIR/server.py"