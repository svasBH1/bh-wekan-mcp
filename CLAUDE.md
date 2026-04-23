# CLAUDE.md — Wekan MCP Server

## Project Info

- **Version:** 0.2.0
- **Owner:** Blockhouse Furniture — IT Department
- **Target Wekan:** v7.60.0 (stability lock)
- **Status:** Active development

## Semantic Versioning

We use [Semantic Versioning](https://semver.org/) (semver) to determine version numbers:
- **MAJOR** (x.0.0) — Breaking changes, API incompatibility
- **MINOR** (0.x.0) — New features, backwards compatible
- **PATCH** (0.0.x) — Bug fixes, backwards compatible

When making code changes (fixes, features, etc.):
1. Bump `__version__` in `server.py` (line 5)
2. Update ALL markdown docs: `grep -r "Version:.*x.y.z" --include="*.md"` 
3. Files requiring version update:
   - `server.py` — `__version__` variable
   - `CLAUDE.md` — Project Info header
   - `PLAN.md` — Project header
   - `TODO.md` — Version line
   - Any test documentation cards in Wekan

**Patch releases (bug fixes):** Increment PATCH (0.0.X)
**Minor releases (new features):** Increment MINOR and reset PATCH to 0
**Major releases (breaking changes):** Increment MAJOR and reset MINOR/PATCH to 0

## The Mission

Maintain and extend the Wekan MCP server that enables AI agents to interface with Blockhouse IT's Wekan project board via Model Context Protocol.

---

## Architecture & Infrastructure

- **Integration Layer:** MCP Python SDK (FastMCP) + `requests` (raw REST, no `python-wekan`).
- **Wekan Instance:** `https://projects.blockhouse.com`
- **Auth:** Bearer token via IT-BOT service account from `.env` (WEKAN_API_TOKEN, WEKAN_USER_ID).
- **Deployment:** Install to `/opt/wekan-mcp` (created by `install.sh`). Run by MCP client directly via stdio.
- **No systemd required** — MCP servers using stdio run on-demand when the client connects.

### Wekan Source Code Reference

Cloned Wekan v7.60 source at `wekan-src/` for API inspection:
- `wekan-src/models/checklistItems.js` — Checklist item endpoints
- `wekan-src/public/api/wekan.yml` — API specification
- Use this to verify expected request/response formats when debugging API issues.

### Project Structure

```
wekan-mcp/
├── server.py              # MCP server (FastMCP, stdio)
├── setup_wekan.py         # Interactive credential helper (--validate, --config)
├── install.sh             # Production installer
├── requirements.txt       # Pinned deps: mcp, python-dotenv, requests, urllib3
├── .env.example          # Config template (NEVER commit .env)
├── .gitignore            # .env, venv/, __pycache__/, *.pyc, wekan-src/
├── tests/                # Unit tests
├── README.md             # Production guide for end users
├── PLAN.md              # Project status, open issues
├── CLAUDE.md            # This file — dev context for AI agents
├── TODO.md             # Active tasks
└── wekan-src/         # Cloned Wekan v7.60 source (reference only)
```

---

## Operational Mandates

### Security
### Deployment
```bash
# Install
bash install.sh

# Setup credentials
nano /opt/wekan-mcp/.env
/opt/wekan-mcp/venv/bin/python /opt/wekan-mcp/setup_wekan.py --validate
```

**Usage:** Configure your MCP client to run the server via stdio:
```
/opt/wekan-mcp/venv/bin/python /opt/wekan-mcp/server.py
```
```

---

## MCP Tools (server.py)

| Tool | Parameters | Notes |
|------|------------|-------|
| `get_mcp_version` | — | Returns MCP server version (v0.2.0) |
| `get_wekan_version` | — | Returns Wekan version (scrapes /information or falls back to WEKAN_VERSION env) |
| `get_allowed_colors` | — | Returns 25 valid card colors (Wekan v7.60.0 ALLOWED_COLORS) |
| `test_connection` | — | Tests Wekan connectivity |
| `list_boards` | — | Lists accessible boards |
| `get_board` | `board_id` | Returns id, title, description, permission |
| `get_lists` | `board_id` | Returns id, title, boardId per list |
| `get_cards` | `board_id`, `list_id` | Returns id, title, listId per card |
| `get_card` | `board_id`, `list_id`, `card_id` | Returns full card details (description, labels, dates, color, labelIds) |
| `get_card_color` | `board_id`, `list_id`, `card_id` | Returns card's current color |
| `set_card_color` | `board_id`, `list_id`, `card_id`, `color` | Sets card color (validates against ALLOWED_COLORS) |
| `create_list` | `board_id`, `title` | POST to create list |
| `add_card` | `board_id`, `list_id`, `title`, `description?`, `swimlane_id?` | Creates new card |
| `update_card` | `board_id`, `list_id`, `card_id`, `title?`, `description?`, `color?` | Updates card (color added v0.1.2) |
| `delete_card` | `board_id`, `list_id`, `card_id` | Deletes card |
| `move_card` | `board_id`, `from_list_id`, `to_list_id`, `card_id`, `position?` | Moves card; position: "top", "bottom", or numeric |
| `search_cards` | `board_id`, `query` | Server-side search with `?query=` param |
| `get_comments` | `board_id`, `card_id` | GET comments (field name is `comment`, not `text`) |
| `add_comment` | `board_id`, `card_id`, `text` | Adds comment; uses `{"comment": text}` per Wekan API |
| `get_comment` | `board_id`, `card_id`, `comment_id` | Returns single comment |
| `get_checklists` | `board_id`, `card_id` | Returns checklists with items |
| `get_checklist_item` | `board_id`, `card_id`, `checklist_id`, `item_id` | Returns single checklist item |
| `add_checklist` | `board_id`, `card_id`, `title` | Creates checklist on card |
| `add_checklist_item` | `board_id`, `card_id`, `checklist_id`, `text` | Adds item; uses `{"title": text}` per Wekan API |
| `update_checklist_item` | `board_id`, `card_id`, `checklist_id`, `item_id`, `is_finished?`, `title?` | Updates item completion state or title; at least one required |
| `delete_checklist_item` | `board_id`, `card_id`, `checklist_id`, `item_id` | Deletes a checklist item |
| `get_board_labels` | `board_id` | Returns board labels `[{id, name, color}]` |
| `add_board_label` | `board_id`, `name`, `color` | Adds label to board via PUT |
| `edit_board_label` | `board_id`, `label_id`, `name?`, `color?` | Edits label (read-modify-push) |
| `add_card_label` | `board_id`, `list_id`, `card_id`, `label_id` | Adds label to card (read-modify-push labelIds) |
| `remove_card_label` | `board_id`, `list_id`, `card_id`, `label_id` | Removes label from card |
| `get_custom_fields` | `board_id` | Returns id, name, type per field |
| `set_custom_field` | `board_id`, `list_id`, `card_id`, `field_id`, `value` | Sets field value |

---

## Wekan v7.60 API Quirks Discovered

### Correct Endpoints
- `get_card`: Use `/api/boards/{board_id}/lists/{list_id}/cards/{card_id}`, NOT `/api/cards/{card_id}`
- `get_comments`: Separate endpoint `/api/boards/{board_id}/cards/{card_id}/comments`
- `get_checklists`: Separate endpoint `/api/boards/{board_id}/cards/{card_id}/checklists`

### Request Body Fields
- Checklist items: Use `{"title": text}`, NOT `{"text": text}` (verified in Wekan source `checklistItems.js` line 314)
- Comments: Use `{"comment": text}`, NOT `{"text": text}`

### Card Color and Labels (v0.1.2)
- Card color: PUT `/api/boards/{board_id}/lists/{list_id}/cards/{card_id}` with `{"color": colorName}`.
- `get_card` returns `color` and `labelIds` (v0.1.2+).
- Board labels: `[{_id, name, color}]` stored on board. Read via GET `/api/boards/{board_id}`.
- Add board label: PUT `/api/boards/{board_id}/labels` with `{"label": {"name": name, "color": color}}`.
- Edit board label: read + modify + push whole `labels` array (no dedicated endpoint).
- Card `labelIds`: read + append/remove + push (no dedicated endpoint).

### Checklist and Comment Reading (v0.1.4)
- `get_checklists`: Bulk endpoint `/checklists` returns checklists without items. Must fetch each individually via `/checklists/{checklistId}` to get items.
- `get_checklist_item`: Fetches single item from checklist's items array (v7.60 doesn't have `/items/:itemId` list endpoint).
- `get_comments`: API returns field as `comment`, not `text`. Same for `get_comment`.

### HTTP Response Handling
- Some endpoints return empty body (204 or empty JSON) — helpers handle this gracefully.

---

## Known Issues (Wekan v7.60)

| Issue | Status | Root Cause |
|-------|--------|-----------|
| Activity user display bug | **Wekan bug** | Frontend shows current viewer instead of activity userId (ReactiveCache lookup returns current session user) |
| Email notifications show "undefined" | **Wekan bug** | userId not resolved in activity creation - likely userId not set in activity document |
| add_checklist_item 500 error | **FIXED** | Request body used wrong field name ("text" instead of "title") |
| add_comment 500 error | **FIXED** | Request body used wrong field name ("text" instead of "comment") |
| get_checklists returns empty items | **FIXED** v0.1.4 | Bulk endpoint returns empty; need to fetch each checklist individually |
| get_comments returns null text | **FIXED** v0.1.4 | API returns field as `comment`, not `text` |
| search_cards returns all cards | **FIXED** v0.1.4 | Wekan doesn't support ?query= param; now filters client-side |

### Activity Display Bug Details

When MCP server actions are performed (move_card, add_checklist, add_checklist_item, etc.):
1. The activity is correctly created in Wekan with the proper `userId` (IT-BOT)
2. However, Wekan's frontend displays the name of whoever is currently viewing the board
3. This is a Wekan v7.60 bug in `ReactiveCache.getUser()` used by `activity.user()` helper
4. The bug manifests as:
   - Steve views board → sees "Stephen Vasilow" in activity
   - IT-BOT views board → sees "Wekan Bot" in activity
   - Riley views board → sees "Riley" in activity
5. Email notifications show "undefined" because the user lookup failed entirely

Workaround: This is a Wekan upstream bug. The MCP server works correctly - the data is stored with the correct userId. Only the frontend display is affected.

---

## When Modifying server.py

1. **Bump version on ANY code change** — See "Semantic Versioning" section above for rules.
2. Update version in: `server.py`, `CLAUDE.md`, `PLAN.md`, `TODO.md`
3. **Always use the HTTP helpers** (`_http_get`, `_http_post`, etc.) — never bare `requests`.
4. **Always validate inputs** with `_validate_id()` or `_validate_nonempty()` before HTTP calls.
5. **Always catch `HTTPError` and `ConnectionError`** explicitly, then `Exception` as fallback.
6. **Return consistent types** — tools return `dict` with `{"error": ...}` on failure, or typed data on success.
7. **Add `@mcp.tool()` decorator** — single decorator only.
8. **Log warnings** for silent fallbacks (e.g., auto-selected swimlane).
9. **Verify API formats** against `wekan-src/` source when debugging endpoint issues.