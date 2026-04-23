# Wekan MCP Server — Development Log

---

## 2026-04-23

### v0.3.0 — Due Dates, Members, Assignees, WIP Limits

**New features:**

- Added `delete_checklist(board_id, card_id, checklist_id)` - deletes entire checklist
- Added `get_list_wip_limit(board_id, list_id)` - read-only WIP limit info `{value, enabled, soft}`
- Added `get_card_due_date(board_id, list_id, card_id)` - returns `dueAt`
- Added `set_card_due_date(board_id, list_id, card_id, due_at)` - sets `dueAt` (ISO 8601)
- Added `get_card_members(board_id, list_id, card_id)` - returns `members` array
- Added `set_card_members(board_id, list_id, card_id, member_ids)` - sets `members` array
- Added `get_card_assignees(board_id, list_id, card_id)` - returns `assignees` array
- Added `set_card_assignees(board_id, list_id, card_id, assignee_ids)` - sets `assignees` array (max 1)
- Added `get_board_users(board_id)` - lists all users on a board (for discovering user IDs)

**Fixes:**

- Fixed `get_card` return fields: `dueAt` (was `dueDate`), `assignees` array (was `assigneeId`), added `members` array

**Limitations documented:**

- Editing checklist titles is not supported by Wekan API
- WIP limits are read-only (cannot set via MCP)

---

### v0.2.0 — Architecture Simplification

Removed systemd service entirely — unnecessary for MCP stdio servers.

**Problem discovered:**

- systemd service was entering a restart loop (counter reached 584!)
- Logs showed: service starts → immediately exits → systemd restarts → repeat
- Root cause: MCP servers with stdio transport run **on-demand**, spawned by the MCP client
- When no client is connected, the process exits — this is by design

**Changes:**

- Deleted `wekan-mcp.service` (systemd unit)
- Simplified `install.sh` — removed service user creation, systemd installation, chown
- No more root required for installation
- MCP client spawns `server.py` directly via stdio

**Lesson learned:**

- MCP stdio servers are NOT long-running daemons — they run only while client is connected
- systemd made sense for traditional REST APIs, but adds no value here
- Should have recognized this mismatch earlier in design phase

---

## 2026-04-23

### v0.2.1 — Bug Fixes

**Fixes:**

- Fixed `move_card` position parsing bug: negative numbers like `-5` now work correctly (previously `isdigit()` returned `False` for negatives, defaulting to `0`)
- Updated CLAUDE.md to remove stale TODO.md reference (DEVLOG.md is used instead)
- Fixed PLAN.md deployment documentation (removed systemd references, service file was deleted in v0.2.0)
- Bumped version to 0.2.1

---

## 2026-04-23

### v0.1.5 — Checklist Item Update/Delete Tools

Added two new tools for checklist item management:

- `update_checklist_item(board_id, card_id, checklist_id, item_id, is_finished?, title?)` — Update item `isFinished` (bool) or `title` (str) via PUT to `/api/boards/{board_id}/cards/{card_id}/checklists/{checklist_id}/items/{item_id}`
- `delete_checklist_item(board_id, card_id, checklist_id, item_id)` — Delete a checklist item via DELETE to the same endpoint

**Live testing on "IT Brain Dump" board:**

- Checked off items on "MCP Tool Test Checklist" and "MCP v0.1.3 Test Checklist" — SUCCESS
- Added new checklist with 2 items, deleted both items — SUCCESS

**Limitations discovered (NOT IMPLEMENTED):**

- **No `update_checklist` tool** — Cannot rename a checklist title (only `update_checklist_item` updates items within a checklist, not the checklist itself)
- **No `delete_checklist` tool** — Cannot delete a checklist (only `delete_checklist_item` deletes items within a checklist)
- The checklist "MCP v0.1.5 Test Checklist" was left behind on the test card because it cannot be deleted via MCP

**To implement in future version:**

- `update_checklist(board_id, card_id, checklist_id, title)` — PUT to `/api/boards/{board_id}/cards/{card_id}/checklists/{checklist_id}` with `{"title": title}`
- `delete_checklist(board_id, card_id, checklist_id)` — DELETE to `/api/boards/{board_id}/cards/{card_id}/checklists/{checklist_id}`

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
