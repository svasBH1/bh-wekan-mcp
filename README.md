# Wekan MCP Server

Internal MCP server for Blockhouse IT Wekan integration. Enables AI agents to
interface with the Blockhouse IT project board via Model Context Protocol.

---

## Quick Install

```bash
bash install.sh
```

This installs to `/opt/wekan-mcp` and creates a Python venv.

---

## Post-Install Steps

After `install.sh` completes:

```bash
# 1. Edit credentials
nano /opt/wekan-mcp/.env

# 2. Verify credentials
/opt/wekan-mcp/venv/bin/python /opt/wekan-mcp/setup_wekan.py --validate
```

---

## Configuration

Edit `/opt/wekan-mcp/.env`:

```
WEKAN_URL=https://projects.blockhouse.com
WEKAN_API_TOKEN=your_token_here
WEKAN_USER_ID=your_user_id_here
```

- `WEKAN_API_TOKEN` — Bearer token from `POST /users/login`
- `WEKAN_USER_ID` — Service account user ID

### Generating Credentials

```bash
/opt/wekan-mcp/venv/bin/python /opt/wekan-mcp/setup_wekan.py
```

---

## Usage

Configure your MCP client to run the server via stdio:

```
/opt/wekan-mcp/venv/bin/python /opt/wekan-mcp/server.py
```

The MCP server uses stdio transport — it's spawned on-demand by the client and
exits when the client disconnects. No systemd service or daemon required.

---

## Available Tools

... (tools table) ...

---

## AI Agent Integration

Configure your MCP client to run the server via stdio:

```json
{
  "mcp_servers": {
    "wekan": {
      "command": "/opt/wekan-mcp/venv/bin/python",
      "args": ["/opt/wekan-mcp/server.py"]
    }
  }
}
```

The server reads `.env` from `/opt/wekan-mcp`. No env vars need to be passed explicitly.

---

## Upgrade

```bash
bash install.sh
```

The installer is idempotent — rerun to update files and requirements.

---

## Uninstall

```bash
rm -rf /opt/wekan-mcp
```