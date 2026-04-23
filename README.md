# Wekan MCP Server

Internal MCP server for Blockhouse IT Wekan integration. Enables AI agents to
interface with the Blockhouse IT project board via Model Context Protocol.

---

## Quick Install

```bash
bash install.sh
```

This installs to `/opt/wekan-mcp`, creates a Python venv, and copies .env credentials.

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

The server reads `.env` from its working directory (`/opt/wekan-mcp`). No env vars need to be passed explicitly.

---

## Configuration

After `install.sh` completes, edit credentials:

```bash
nano /opt/wekan-mcp/.env
```

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

### Verify Credentials

```bash
cd /opt/wekan-mcp
python3 setup_wekan.py --validate
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
| `get_card` | `board_id`, `list_id`, `card_id` | Get full card details |
| `add_card` | `board_id`, `list_id`, `title`, `description?` | Add a new card |
| `update_card` | `board_id`, `list_id`, `card_id`, `title?`, `description?`, `color?` | Update card |
| `delete_card` | `board_id`, `list_id`, `card_id` | Delete a card |
| `move_card` | `board_id`, `from_list_id`, `to_list_id`, `card_id`, `position?` | Move card |
| `create_list` | `board_id`, `title` | Create a new list |
| `search_cards` | `board_id`, `query` | Search cards by title/description |
| `get_checklists` | `board_id`, `card_id` | Get checklists with items |
| `get_checklist_item` | `board_id`, `card_id`, `checklist_id`, `item_id` | Get checklist item |
| `add_checklist` | `board_id`, `card_id`, `title` | Add checklist to card |
| `add_checklist_item` | `board_id`, `card_id`, `checklist_id`, `text` | Add item to checklist |
| `update_checklist_item` | `board_id`, `card_id`, `checklist_id`, `item_id`, `is_finished?`, `title?` | Update item |
| `delete_checklist_item` | `board_id`, `card_id`, `checklist_id`, `item_id` | Delete item |
| `get_comments` | `board_id`, `card_id` | Get comments on card |
| `add_comment` | `board_id`, `card_id`, `text` | Add comment |
| `get_custom_fields` | `board_id` | Get custom fields on board |
| `set_custom_field` | `board_id`, `list_id`, `card_id`, `field_id`, `value` | Set custom field |
| `get_allowed_colors` | — | Get 25 valid card colors |
| `get_card_color` | `board_id`, `list_id`, `card_id` | Get card color |
| `set_card_color` | `board_id`, `list_id`, `card_id`, `color` | Set card color |
| `get_board_labels` | `board_id` | Get board labels |
| `add_board_label` | `board_id`, `name`, `color` | Add label to board |
| `add_card_label` | `board_id`, `list_id`, `card_id`, `label_id` | Add label to card |
| `remove_card_label` | `board_id`, `list_id`, `card_id`, `label_id` | Remove label from card |

---

## Troubleshooting

**"Connection failed" errors** — verify `WEKAN_URL` is reachable from this machine:

```bash
curl -I https://projects.blockhouse.com
```