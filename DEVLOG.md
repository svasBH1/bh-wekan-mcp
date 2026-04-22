# Wekan MCP Server — Development Log

---

## 2026-04-22

### v0.1.4 — Checklist/Comment Reading Fixes

Fixed two API quirks discovered during live testing:

- `get_checklists` bulk endpoint returns empty items array — now fetches each checklist individually via `/checklists/{checklistId}` to get items.
- `get_comments` API returns field as `comment`, not `text` — same for `get_comment`.

Added two new tools: `get_checklist_item(board_id, card_id, checklist_id, item_id)` and `get_comment(board_id, card_id, comment_id)`.

### v0.1.2 — Card Color and Label Tools

Added full label and color management:

- `get_allowed_colors()` — returns 25 valid colors from Wekan ALLOWED_COLORS
- `get_card_color()` / `set_card_color()` — get/set card color via PUT
- `get_board_labels()` / `add_board_label()` / `edit_board_label()` — board label CRUD
- `add_card_label()` / `remove_card_label()` — card label management (read-modify-push on labelIds array)
- `get_card()` now returns `color` and `labelIds`
- `update_card()` accepts `color` parameter

23 unit tests + 6 live tests pass.

### v0.1.1 — Activity Display Bug Investigation

Determined that the activity display bug is a Wekan v7.60 frontend issue, not an MCP server bug:

- MCP server correctly sends actions with IT-BOT userId in request body
- Activity IS created with correct userId in Wekan database
- Wekan frontend displays current viewer's name instead of activity userId (ReactiveCache bug)
- Email notifications show "undefined" because userId lookup fails entirely
- Verified: add_checklist_item, add_comment, move_card all work correctly

### Initial Development

- Built MCP server using FastMCP SDK + requests (raw REST, no python-wekan dependency)
- 25 tools covering boards, lists, cards, checklists, comments, labels, custom fields
- Input validation via `_validate_id()` and `_validate_nonempty()`
- HTTP helpers with retry logic (3 retries, backoff 0.5s on 429/500/502/503/504)
- Connection pooling via Session with HTTPAdapter
- Credential helper (`setup_wekan.py`) for interactive token capture
- Production installer (`install.sh`) → systemd service at `/opt/wekan-mcp`
- Target Wekan: v7.60.0 (stability lock)
