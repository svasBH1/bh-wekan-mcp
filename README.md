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

| Tool | Description |
|------|-------------|
| `list_boards` | List all accessible boards |
| `get_board` | Get board details |
| `get_lists` | Get lists in a board |
| `get_cards` | Get cards in a list |
| `get_card` | Get full card details |
| `add_card` | Create a new card |
| `update_card` | Update card title/description/color |
| `delete_card` | Delete a card |
| `move_card` | Move card to another list |
| `search_cards` | Search cards by query |
| `get_comments` / `add_comment` | Manage card comments |
| `get_checklists` / `add_checklist` | Manage checklists |
| `get_card_color` / `set_card_color` | Manage card colors |
| `get_board_labels` / `add_board_label` | Manage board labels |
| `add_card_label` / `remove_card_label` | Manage card labels |
| `get_custom_fields` / `set_custom_field` | Manage custom fields |

---

## Troubleshooting

### Connection refused

Verify credentials in `.env` and test:

```bash
/opt/wekan-mcp/venv/bin/python /opt/wekan-mcp/setup_wekan.py --validate
```

### Tool errors

Check `.env` has valid `WEKAN_API_TOKEN` and `WEKAN_USER_ID`. Token must not be
expired or revoked.

---

## Upgrade

```bash
bash install.sh
```

The installer is idempotent — rerun to update files and requirements.

---

## Uninstall

```bash
sudo rm -rf /opt/wekan-mcp
```

If you previously installed the systemd service:

```bash
sudo systemctl stop wekan-mcp
sudo systemctl disable wekan-mcp
sudo rm /etc/systemd/system/wekan-mcp.service
sudo systemctl daemon-reload
```