# Wekan MCP Server

Internal MCP server for Blockhouse IT Wekan integration. Enables AI agents to
interface with the Blockhouse IT project board via Model Context Protocol.

---

## Quick Install

```bash
sudo bash install.sh
```

This installs to `/opt/wekan-mcp`, creates a Python venv, and enables the
`wekan-mcp` systemd service.

---

## Post-Install Steps

After `install.sh` completes:

```bash
# 1. Edit credentials
nano /opt/wekan-mcp/.env

# 2. Verify credentials (optional but recommended)
cd /opt/wekan-mcp
python3 setup_wekan.py --validate

# 3. Start the service
sudo systemctl start wekan-mcp

# 4. Verify it's running
sudo systemctl status wekan-mcp
```

---

## Configuration

Edit `/opt/wekan-mcp/.env`:

```
WEKAN_URL=https://projects.blockhouse.com
WEKAN_API_TOKEN=your_token_here
WEKAN_USER_ID=your_user_id_here
```

- `WEKAN_URL` — Wekan instance URL
- `WEKAN_API_TOKEN` — Bearer token from `POST /users/login`
- `WEKAN_USER_ID` — Service account user ID (required for card/comment authorship)

### Generating Credentials

For interactive token capture:

```bash
cd /opt/wekan-mcp
python3 setup_wekan.py
```

---

## Credential Rotation

To refresh the API token:

```bash
cd /opt/wekan-mcp
python3 setup_wekan.py
```

Or validate current credentials without updating:

```bash
python3 setup_wekan.py --validate
```

After updating `.env`, restart the service:

```bash
sudo systemctl restart wekan-mcp
```

---

## Service Management

```bash
sudo systemctl status wekan-mcp
sudo systemctl restart wekan-mcp
sudo systemctl stop wekan-mcp
journalctl -u wekan-mcp -f
```

The service runs as the `wekan-mcp` system user (created by `install.sh`).

---

## Troubleshooting

**Service fails to start** — check credentials:
```bash
journalctl -u wekan-mcp -n 50
python3 /opt/wekan-mcp/setup_wekan.py --validate
```

**"Connection failed" errors** — verify `WEKAN_URL` is reachable from this machine:
```bash
curl -I https://projects.blockhouse.com
```

---

## MCP Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `test_connection` | — | Test connectivity to Wekan |
| `list_boards` | — | List all accessible boards |
| `get_board` | `board_id` | Get board details |
| `get_lists` | `board_id` | Get all lists in a board |
| `get_cards` | `board_id`, `list_id` | Get all cards in a list |
| `add_card` | `board_id`, `list_id`, `title`, `description?` | Add a new card |
| `update_card` | `board_id`, `list_id`, `card_id`, `title?`, `description?` | Update card |
| `delete_card` | `board_id`, `list_id`, `card_id` | Delete a card |
| `create_list` | `board_id`, `title` | Create a new list |
| `search_cards` | `board_id`, `query` | Search cards by title/description |
| `get_custom_fields` | `board_id` | Get custom fields on board |
| `set_custom_field` | `board_id`, `list_id`, `card_id`, `field_id`, `value` | Set custom field |
| `get_comments` | `card_id` | Get comments on a card |
| `add_comment` | `board_id`, `card_id`, `text` | Add a comment |

---

## AI Agent Integration

Add to your MCP client config:

```json
{
  "mcp_servers": {
    "wekan": {
      "command": "python3",
      "args": ["/opt/wekan-mcp/server.py"]
    }
  }
}
```

The server reads `.env` from its working directory (`/opt/wekan-mcp`). No env
vars need to be passed explicitly.
