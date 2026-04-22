#!/bin/bash
# Wekan MCP Server - Production Installer
# Must be run as root: sudo bash install.sh
set -e

SERVICE_NAME="wekan-mcp"
INSTALL_DIR="/opt/wekan-mcp"

# Root guard
if [ "$EUID" != 0 ]; then
    echo "Error: This script must be run as root (sudo bash install.sh)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Wekan MCP Server Installer ==="
echo ""

# Create dedicated service user if it doesn't exist
if ! getent group wekan-mcp >/dev/null 2>&1; then
    echo "Creating system group 'wekan-mcp'..."
    groupadd --system wekan-mcp
fi

if ! getent passwd wekan-mcp >/dev/null 2>&1; then
    echo "Creating system user 'wekan-mcp'..."
    useradd --system --no-create-home --shell /usr/sbin/nologin --gid wekan-mcp wekan-mcp
fi
echo "Using user 'wekan-mcp'."
echo ""

# Install (idempotent)
echo "Installing to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Copy app files only if changed
for f in server.py requirements.txt setup_wekan.py wekan-mcp.service; do
    if [ ! -f "$INSTALL_DIR/$f" ] || [ "$SCRIPT_DIR/$f" -nt "$INSTALL_DIR/$f" ]; then
        cp "$SCRIPT_DIR/$f" "$INSTALL_DIR/$f"
    fi
done

# Copy .env only if it doesn't exist (preserve user credentials)
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$INSTALL_DIR/.env"
    echo "Created $INSTALL_DIR/.env — edit it with your credentials before starting the service."
else
    # Verify existing .env has valid credentials
    if grep -q "your_token_here\|your_user_id_here" "$INSTALL_DIR/.env" 2>/dev/null; then
        echo "Warning: $INSTALL_DIR/.env still contains placeholder values."
    fi
fi

# Install systemd service
cp "$SCRIPT_DIR/wekan-mcp.service" /etc/systemd/system/

# Python venv (idempotent)
echo "Setting up Python environment..."
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
fi

# Only reinstall requirements if requirements.txt changed
if [ ! -f "$INSTALL_DIR/.requirements_hash" ] || [ "$INSTALL_DIR/requirements.txt" -nt "$INSTALL_DIR/.requirements_hash" ] || ! echo "$(cat "$INSTALL_DIR/requirements.txt")" | sha256sum -c "$INSTALL_DIR/.requirements_hash" 2>/dev/null; then
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    sha256sum "$INSTALL_DIR/requirements.txt" > "$INSTALL_DIR/.requirements_hash"
fi

# Set ownership to wekan-mcp user
echo "Setting ownership to wekan-mcp..."
chown -R wekan-mcp:wekan-mcp "$INSTALL_DIR"

# Enable service (do not start yet — .env has placeholder creds)
echo "Enabling systemd service..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo ""
echo "=== Install Complete ==="
echo "Service: $SERVICE_NAME"
echo ""
echo "Next steps:"
echo "  1. Edit $INSTALL_DIR/.env with your credentials"
echo "  2. $INSTALL_DIR/venv/bin/python $INSTALL_DIR/setup_wekan.py   # interactive credential capture"
echo "  3. systemctl start $SERVICE_NAME"
echo "  4. systemctl status $SERVICE_NAME"
echo "  5. journalctl -u $SERVICE_NAME -f       # watch logs"
