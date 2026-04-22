# PLAN.md — Wekan MCP Server

**Project:** `wekan-mcp` — Internal MCP server for Blockhouse IT Wekan integration
**Version:** 0.1.4 (semver)
**Owner:** Blockhouse Furniture — IT Department
**Target Wekan:** v7.60.0
**Wekan Instance:** `https://projects.blockhouse.com`
**Status:** Active development

---

## Architecture

```
AI Agent (OpenCode/Gemini)
           ↓
      MCP Client
           ↓
   FastMCP Server (server.py)
           ↓
    Wekan REST API
           ↓
     Wekan v7.60
```

### Stack
- **MCP SDK:** MCP Python SDK (FastMCP)
- **Auth:** Bearer token via IT-BOT service account
- **Config:** `.env` file
- **Deployment:** systemd service at `/opt/wekan-mcp`

---

## Project Structure

```
wekan-mcp-experimental/
├── .env                 # Secrets (git-ignored)
├── .env.example         # Template
├── .gitignore          # .env, venv/, __pycache__/, wekan-src/
├── requirements.txt    # mcp, python-dotenv, requests
├── server.py           # MCP server (stdio)
├── setup_wekan.py      # Interactive credential helper
├── install.sh         # Root-only production installer
├── wekan-mcp.service  # systemd unit file
├── README.md           # Production guide
├── CLAUDE.md          # Dev context
├── PLAN.md           # This file
├── TODO.md
└── wekan-src/        # Cloned Wekan v7.60 source (reference only)
```

---

## Deployment

### Install (root)
```bash
sudo bash install.sh
```

### Credential Rotation
```bash
cd /opt/wekan-mcp
python3 setup_wekan.py
```

### Service Management
```bash
systemctl status wekan-mcp
systemctl restart wekan-mcp
journalctl -u wekan-mcp -f
```

### AI Agent Config
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

---

## Completed

### Core Infrastructure (v0.1.0)
- [x] `setup_wekan.py` — Interactive credential helper with `--validate`
- [x] `install.sh` — Root-only production installer (systemd)
- [x] `wekan-mcp.service` — systemd unit file
- [x] `.gitignore` created (`.env`, `venv/`, `__pycache__/`, `wekan-src/`)

### MCP Tools
- [x] `test_connection` — Test Wekan connectivity
- [x] `list_boards` — List accessible boards
- [x] `get_board` — Get board details
- [x] `get_lists` — Get all lists in board
- [x] `get_cards` — Get all cards in list
- [x] `get_card` — Get full card details (discovered correct endpoint)
- [x] `create_list` — Create new list
- [x] `add_card` — Add card to list
- [x] `update_card` — Update card title/description
- [x] `delete_card` — Delete card
- [x] `move_card` — Move card between lists
- [x] `search_cards` — Search cards by query
- [x] `get_comments` — Get comments (discovered correct endpoint)
- [x] `get_checklists` — Get checklists with items
- [x] `add_checklist` — Create checklist on card
- [x] `add_checklist_item` — Add item (FIXED: uses `{"title"}` not `{"text"}`)
- [x] `add_comment` — Add comment (FIXED: uses `{"comment"}` not `{"text"}`)
- [x] `get_custom_fields` — Get custom fields
- [x] `set_custom_field` — Set custom field value

### API Discovery & Fixes
- [x] `get_card`: Use `/api/boards/{board_id}/lists/{list_id}/cards/{card_id}`
- [x] `get_comments`: Use separate `/api/boards/{board_id}/cards/{card_id}/comments`
- [x] `get_checklists`: Use separate `/api/boards/{board_id}/cards/{card_id}/checklists`
- [x] `add_checklist_item`: Changed request body from `{"text"}` to `{"title"}` per Wekan source
- [x] HTTP helpers: Handle empty responses (204, empty body)
- [x] Cloned Wekan v7.60 source for API reference

### Card Color & Label Tools (v0.1.2)
- [x] `get_allowed_colors()` — Returns 25 valid card colors (ALLOWED_COLORS)
- [x] `get_card_color()` — Returns card's current color
- [x] `set_card_color()` — Sets card color via PUT with `{"color": colorName}`
- [x] `get_board_labels()` — Returns board labels `[{id, name, color}]`
- [x] `add_board_label()` — Adds label via PUT `/api/boards/{board_id}/labels`
- [x] `edit_board_label()` — Edits label (read-modify-push array)
- [x] `add_card_label()` — Adds label to card (read-modify-push labelIds)
- [x] `remove_card_label()` — Removes label from card
- [x] `get_card()` — Now returns `color` and `labelIds`
- [x] `update_card()` — Now accepts `color` parameter
- [x] 23 unit tests + 6 live tests pass

---

## Open Issues

### Wekan v7.60 Upstream Bugs (NOT MCP Server Bugs)
| Issue | Error | Status |
|-------|-------|--------|
| Activity user display bug | Activities show current viewer's name instead of userId | **Wekan ReactiveCache bug** - frontend displays wrong user |
| Email shows "undefined" | User lookup fails in notifications | **Wekan bug** - userId not resolved |

**Explanation:** The MCP server correctly sends userId in API requests. Activities ARE created with correct userId in Wekan database. The display bug is in Wekan's frontend `ReactiveCache.getUser()` which returns the current session user instead of the activity's userId. This is a Wekan v7.60 bug, not an MCP server bug.

### Future Considerations
- Consider supporting multiple Wekan versions if needed
- May create Blockhouse wekan-mcp git repo (not yet created)
- Document IT-BOT service account credential rotation process