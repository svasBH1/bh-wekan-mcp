"""
Wekan MCP Server
Model Context Protocol server for Wekan
"""
__version__ = "0.3.2"

import os
import sys
import logging
import time
import re
from typing import Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

WEKAN_URL = os.getenv("WEKAN_URL", "https://projects.blockhouse.com")
API_TOKEN = os.getenv("WEKAN_API_TOKEN", "")
USER_ID = os.getenv("WEKAN_USER_ID", "")
WEKAN_VERSION = os.getenv("WEKAN_VERSION", "7.60.0")

ALLOWED_COLORS = [
    "white", "green", "yellow", "orange", "red", "purple", "blue", "sky",
    "lime", "pink", "black", "silver", "peachpuff", "crimson", "plum",
    "darkgreen", "slateblue", "magenta", "gold", "navy", "gray",
    "saddlebrown", "paleturquoise", "mistyrose", "indigo",
]

# Validate required configuration before server starts
if not WEKAN_URL:
    print("FATAL: WEKAN_URL is not set in .env", file=sys.stderr)
    sys.exit(1)
if not API_TOKEN or API_TOKEN in ("your_token_here", ""):
    print("FATAL: WEKAN_API_TOKEN is not set or still has placeholder value in .env", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wekan-mcp")

mcp = FastMCP("wekan-mcp")


@mcp.tool()
def get_mcp_version() -> dict:
    """Get MCP server version for debugging."""
    return {"version": __version__}


@mcp.tool()
def get_wekan_version() -> dict:
    """Get Wekan version from the Wekan instance /information page."""
    session = _build_session()
    try:
        resp = session.get(
            f"{WEKAN_URL}/information",
            headers=_get_headers(),
            timeout=10,
            allow_redirects=True,
        )
        html = resp.text
        match = re.search(r'WeKan\s+®\s+Version.*?<td>(\d+\.\d+\.\d+)</td>', html, re.DOTALL)
        if match:
            return {"version": match.group(1)}
    except Exception:
        pass
    return {"version": WEKAN_VERSION}


# ---------------------------------------------------------------------------
# HTTP session with retry/backoff (Issue #7, #3)
# ---------------------------------------------------------------------------

def _build_session() -> requests.Session:
    """Create a requests.Session with connection pooling and retry logic."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _get_headers() -> dict:
    return {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}


# ---------------------------------------------------------------------------
# Shared HTTP helpers (Issue #2, #7)
# ---------------------------------------------------------------------------

def _http_get(session: requests.Session, url: str, **kwargs) -> Optional[dict]:
    """GET with raise_for_status. Returns parsed JSON, None on empty response."""
    resp = session.get(url, headers=_get_headers(), timeout=10, **kwargs)
    resp.raise_for_status()
    if resp.status_code == 204 or not resp.text:
        return None
    return resp.json()


def _http_post(session: requests.Session, url: str, **kwargs) -> Optional[dict]:
    """POST with raise_for_status. Returns parsed JSON, None on empty response."""
    resp = session.post(url, headers=_get_headers(), timeout=10, **kwargs)
    resp.raise_for_status()
    if resp.status_code == 204 or not resp.text:
        return None
    return resp.json()


def _http_put(session: requests.Session, url: str, **kwargs) -> Optional[dict]:
    """PUT with raise_for_status. Returns parsed JSON, None on empty response."""
    resp = session.put(url, headers=_get_headers(), timeout=10, **kwargs)
    resp.raise_for_status()
    if resp.status_code == 204 or not resp.text:
        return None
    return resp.json()


def _http_delete(session: requests.Session, url: str, **kwargs) -> bool:
    """DELETE with raise_for_status. Returns True on 2xx."""
    resp = session.delete(url, headers=_get_headers(), timeout=10, **kwargs)
    return 200 <= resp.status_code < 300


# ---------------------------------------------------------------------------
# Input validation helpers (Issue #8)
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"^[A-Za-z0-9]+$")


def _validate_id(value: str, name: str) -> str:
    """Validate a Wekan ID field. Raises ValueError on bad input."""
    if not value or not _ID_RE.match(value):
        raise ValueError(f"{name} must be a non-empty alphanumeric string, got: {value!r}")
    return value


def _validate_nonempty(value: str, name: str) -> str:
    """Validate a non-empty string field."""
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{name} must be a non-empty string, got: {value!r}")
    return stripped


def _validate_color(color: str) -> str:
    """Validate a card color against ALLOWED_COLORS."""
    color = _validate_nonempty(color, "color")
    if color not in ALLOWED_COLORS:
        raise ValueError(
            f"color must be one of {ALLOWED_COLORS}, got: {color!r}"
        )
    return color


# ---------------------------------------------------------------------------
# Swimlane helper (Issue #14)
# ---------------------------------------------------------------------------

def _get_swimlanes(board_id: str, session: requests.Session) -> list[dict]:
    """Get swimlanes for a board. Returns empty list on failure."""
    try:
        data = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/swimlanes")
        if isinstance(data, list):
            return [{"id": s.get("_id"), "title": s.get("title")} for s in data]
        return []
    except Exception:
        logger.exception("Failed to fetch swimlanes for board %s", board_id)
        return []


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def test_connection() -> str:
    """Test connectivity to Wekan and return status."""
    session = _build_session()
    try:
        data = _http_get(session, f"{WEKAN_URL}/api/boards")
        if isinstance(data, list):
            return f"Connected. Access to {len(data)} boards."
        # Non-admin users get 403 on /api/boards — verify via /api/user
        data = _http_get(session, f"{WEKAN_URL}/api/user")
        if isinstance(data, dict):
            active_boards = [b for b in data.get("boards", []) if b.get("isActive")]
            return f"Connected. Access to {len(active_boards)} board(s)."
        return "Error: Unexpected response from Wekan API"
    except requests.exceptions.HTTPError as e:
        return f"HTTP error: {e.response.status_code}"
    except requests.exceptions.ConnectionError as e:
        return f"Connection failed: {e}"
    except Exception as e:
        return f"Connection failed: {e}"


@mcp.tool()
def list_boards() -> list[dict]:
    """List all accessible boards."""
    session = _build_session()
    try:
        data = _http_get(session, f"{WEKAN_URL}/api/boards")
        if isinstance(data, list):
            return [{"id": b.get("_id"), "title": b.get("title")} for b in data]
        # Non-admin users get 403 on /api/boards — fall back to /api/user
        data = _http_get(session, f"{WEKAN_URL}/api/user")
        if isinstance(data, dict):
            user_boards = data.get("boards", [])
            if user_boards:
                result = []
                for b in user_boards:
                    if b.get("isActive"):
                        board_id = b.get("boardId")
                        try:
                            board_data = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}")
                            result.append({"id": board_id, "title": board_data.get("title", "")})
                        except Exception:
                            result.append({"id": board_id, "title": ""})
                return result
        return []
    except requests.exceptions.HTTPError as e:
        return [{"error": f"HTTP {e.response.status_code}"}]
    except requests.exceptions.ConnectionError as e:
        return [{"error": f"Connection failed: {e}"}]
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_board(board_id: str) -> dict:
    """Get board details by ID."""
    _validate_id(board_id, "board_id")
    session = _build_session()
    try:
        board = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}")
        if isinstance(board, dict):
            return {
                "id": board.get("_id"),
                "title": board.get("title"),
                "description": board.get("description"),
                "permission": board.get("permission"),
            }
        return {"error": "Unexpected response from Wekan API"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_lists(board_id: str) -> list[dict]:
    """Get all lists in a board."""
    _validate_id(board_id, "board_id")
    session = _build_session()
    try:
        lists = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/lists")
        if isinstance(lists, list):
            return [{"id": l.get("_id"), "title": l.get("title"), "boardId": l.get("boardId")} for l in lists]
        return []
    except requests.exceptions.HTTPError as e:
        return [{"error": f"HTTP {e.response.status_code}"}]
    except requests.exceptions.ConnectionError as e:
        return [{"error": f"Connection failed: {e}"}]
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_list_wip_limit(board_id: str, list_id: str) -> dict:
    """Get the WIP (Work In Progress) limit settings for a list.

    Returns: {"value": int, "enabled": bool, "soft": bool}

    WIP limits control how many cards can be in a list. Read-only - MCP server
    cannot modify WIP limits.
    """
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    session = _build_session()
    try:
        list_data = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}")
        if isinstance(list_data, dict):
            wip = list_data.get("wipLimit") or {}
            return {
                "value": wip.get("value") or 0,
                "enabled": wip.get("enabled") or False,
                "soft": wip.get("soft") or False,
            }
        return {"value": 0, "enabled": False, "soft": False}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_cards(board_id: str, list_id: str) -> list[dict]:
    """Get all cards in a list."""
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    session = _build_session()
    try:
        cards = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards")
        if isinstance(cards, list):
            return [{"id": c.get("_id"), "title": c.get("title"), "listId": c.get("listId") or list_id} for c in cards]
        return []
    except requests.exceptions.HTTPError as e:
        return [{"error": f"HTTP {e.response.status_code}"}]
    except requests.exceptions.ConnectionError as e:
        return [{"error": f"Connection failed: {e}"}]
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_card(board_id: str, list_id: str, card_id: str) -> dict:
    """Get full card details including description, labels, due date, etc."""
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    session = _build_session()
    try:
        card = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
        if isinstance(card, dict):
            return {
                "id": card.get("_id"),
                "title": card.get("title"),
                "description": card.get("description") or "",
                "listId": card.get("listId") or list_id,
                "swimlaneId": card.get("swimlaneId") or "",
                "dueAt": card.get("dueAt") or "",
                "startAt": card.get("startAt") or "",
                "createdAt": card.get("createdAt") or "",
                "assignees": card.get("assignees") or [],
                "members": card.get("members") or [],
                "color": card.get("color") or "",
                "labelIds": card.get("labelIds") or [],
                "labels": card.get("labels") or [],
            }
        return {"error": "Unexpected response from Wekan API"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_checklists(board_id: str, card_id: str) -> list[dict]:
    """Get checklists on a card."""
    _validate_id(board_id, "board_id")
    _validate_id(card_id, "card_id")
    session = _build_session()
    try:
        checklists = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/cards/{card_id}/checklists")
        if isinstance(checklists, list):
            result = []
            for c in checklists:
                checklist_id = c.get("_id")
                title = c.get("title")
                items = c.get("items", [])
                if not items:
                    items = _get_checklist_items(board_id, card_id, checklist_id, session)
                result.append({"id": checklist_id, "title": title, "items": items})
            return result
        return []
    except requests.exceptions.HTTPError as e:
        return [{"error": f"HTTP {e.response.status_code}"}]
    except requests.exceptions.ConnectionError as e:
        return [{"error": f"Connection failed: {e}"}]
    except Exception as e:
        return [{"error": str(e)}]


def _get_checklist_items(board_id: str, card_id: str, checklist_id: str, session: requests.Session) -> list[dict]:
    """Fetch all items for a checklist via individual endpoint."""
    try:
        url = f"{WEKAN_URL}/api/boards/{board_id}/cards/{card_id}/checklists/{checklist_id}"
        checklist = _http_get(session, url)
        if isinstance(checklist, dict):
            items = checklist.get("items", [])
            return [{"id": i.get("_id"), "title": i.get("title"), "isFinished": i.get("isFinished", False)} for i in items]
    except Exception:
        pass
    return []


@mcp.tool()
def get_checklist_item(board_id: str, card_id: str, checklist_id: str, item_id: str) -> dict:
    """Get a single checklist item by ID."""
    _validate_id(board_id, "board_id")
    _validate_id(card_id, "card_id")
    _validate_id(checklist_id, "checklist_id")
    _validate_id(item_id, "item_id")
    session = _build_session()
    try:
        session.headers.update({"Accept": "application/json"})
        item = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/cards/{card_id}/checklists/{checklist_id}/items/{item_id}")
        if isinstance(item, dict):
            return {
                "id": item.get("_id"),
                "title": item.get("title"),
                "isFinished": item.get("isFinished", False),
            }
        return {"error": "Item not found"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_comment(board_id: str, card_id: str, comment_id: str) -> dict:
    """Get a single comment by ID."""
    _validate_id(board_id, "board_id")
    _validate_id(card_id, "card_id")
    _validate_id(comment_id, "comment_id")
    session = _build_session()
    try:
        comments = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/cards/{card_id}/comments")
        if isinstance(comments, list):
            for c in comments:
                if c.get("_id") == comment_id:
                    return {
                        "id": c.get("_id"),
                        "text": c.get("comment"),
                        "authorId": c.get("authorId"),
                    }
        return {"error": "Comment not found"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def add_checklist(board_id: str, card_id: str, title: str) -> dict:
    """Add a checklist to a card."""
    _validate_id(board_id, "board_id")
    _validate_id(card_id, "card_id")
    _validate_nonempty(title, "title")
    session = _build_session()
    try:
        checklist = _http_post(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/cards/{card_id}/checklists",
            json={"title": title},
        )
        if isinstance(checklist, dict):
            return {"id": checklist.get("_id"), "title": checklist.get("title")}
        return {"error": "Unexpected response from Wekan API"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def add_checklist_item(board_id: str, card_id: str, checklist_id: str, text: str) -> dict:
    """Add an item to a checklist."""
    _validate_id(board_id, "board_id")
    _validate_id(card_id, "card_id")
    _validate_id(checklist_id, "checklist_id")
    _validate_nonempty(text, "text")
    session = _build_session()
    try:
        item = _http_post(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/cards/{card_id}/checklists/{checklist_id}/items",
            json={"title": text},
        )
        if isinstance(item, dict):
            return {"id": item.get("_id"), "title": text}
        return {"error": "Unexpected response from Wekan API"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def create_list(board_id: str, title: str) -> dict:
    """Create a new list in a board."""
    _validate_id(board_id, "board_id")
    _validate_nonempty(title, "title")
    session = _build_session()
    try:
        lst = _http_post(session, f"{WEKAN_URL}/api/boards/{board_id}/lists", json={"title": title})
        if isinstance(lst, dict):
            return {"id": lst.get("_id"), "title": lst.get("title")}
        return {"error": "Unexpected response from Wekan API"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def add_card(board_id: str, list_id: str, title: str, description: str = "", swimlane_id: str = "") -> dict:
    """Add a new card to a list."""
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_nonempty(title, "title")
    session = _build_session()

    # Resolve swimlane if not provided (Issue #5)
    effective_swimlane = swimlane_id.strip() if swimlane_id.strip() else None
    if not effective_swimlane:
        swimlanes = _get_swimlanes(board_id, session)
        if not swimlanes:
            return {"error": "No swimlane found for board — board may be empty or inaccessible"}
        # Use the first default swimlane but log a warning so the user knows
        effective_swimlane = swimlanes[0]["id"]
        logger.warning(
            "swimlane_id not provided; auto-selected default swimlane '%s' for board '%s'. "
            "Pass swimlane_id explicitly to avoid ambiguity.",
            effective_swimlane,
            board_id,
        )

    try:
        card = _http_post(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards",
            json={
                "authorId": USER_ID,
                "title": title,
                "description": description,
                "swimlaneId": effective_swimlane,
            },
        )
        if isinstance(card, dict):
            return {"id": card.get("_id"), "title": card.get("title"), "listId": card.get("listId")}
        return {"error": "Unexpected response from Wekan API"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:100]}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def update_card(board_id: str, list_id: str, card_id: str, title: str = "", description: str = "", color: str = "") -> dict:
    """Update a card's title, description, and/or color."""
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    session = _build_session()
    try:
        payload = {}
        if title:
            payload["title"] = title
        if description:
            payload["description"] = description
        if color:
            _validate_color(color)
            payload["color"] = color
        if not payload:
            return {"error": "At least one of title, description, or color must be provided"}
        card = _http_put(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}",
            json=payload,
        )
        if isinstance(card, dict):
            return {"id": card.get("_id"), "title": card.get("title")}
        return {"error": "Unexpected response from Wekan API"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def delete_card(board_id: str, list_id: str, card_id: str) -> bool:
    """Delete a card."""
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    session = _build_session()
    try:
        return _http_delete(session, f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
    except Exception:
        return False


@mcp.tool()
def move_card(board_id: str, from_list_id: str, to_list_id: str, card_id: str, position: str = "top") -> dict:
    """Move a card to a different list.
    
    Args:
        board_id: The board ID
        from_list_id: Source list ID
        to_list_id: Destination list ID
        card_id: The card ID to move
        position: "top", "bottom", or a numeric sort value (negative = top of list)
    """
    _validate_id(board_id, "board_id")
    _validate_id(from_list_id, "from_list_id")
    _validate_id(to_list_id, "to_list_id")
    _validate_id(card_id, "card_id")
    session = _build_session()
    
    try:
        sort_value = -999999 if position == "top" else (999999 if position == "bottom" else int(position))
    except ValueError:
        sort_value = 0
    
    try:
        card = _http_put(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/lists/{from_list_id}/cards/{card_id}",
            json={"listId": to_list_id, "sort": sort_value},
        )
        if isinstance(card, dict):
            return {"id": card.get("_id"), "title": card.get("title"), "listId": card.get("listId"), "sort": card.get("sort")}
        return {"error": "Unexpected response from Wekan API"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def search_cards(board_id: str, query: str) -> list[dict]:
    """Search cards in a board by title/description.

    Fetches all cards and filters client-side (Wekan doesn't support
    server-side ?query= filtering on the cards endpoint).
    """
    _validate_id(board_id, "board_id")
    _validate_nonempty(query, "query")
    session = _build_session()
    try:
        lists = _get_lists_cached(board_id, session)
        results = []
        query_lower = query.lower()
        for lst in lists:
            list_id = lst.get("id")
            if not list_id:
                continue
            url = f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards"
            cards = _http_get(session, url)
            if isinstance(cards, list):
                for c in cards:
                    title = c.get("title", "")
                    description = c.get("description", "")
                    if query_lower in title.lower() or query_lower in description.lower():
                        results.append({
                            "id": c.get("_id"),
                            "title": title,
                            "listId": list_id,
                        })
        return results
    except requests.exceptions.HTTPError as e:
        return [{"error": f"HTTP {e.response.status_code}"}]
    except requests.exceptions.ConnectionError as e:
        return [{"error": f"Connection failed: {e}"}]
    except Exception as e:
        return [{"error": str(e)}]


def _get_lists_cached(board_id: str, session: requests.Session) -> list[dict]:
    """Fetch lists once and cache in session (lightweight cache)."""
    cache_key = f"_lists_{board_id}"
    if not hasattr(session, cache_key):
        data = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/lists")
        if isinstance(data, list):
            setattr(session, cache_key, [{"id": l.get("_id"), "title": l.get("title"), "boardId": l.get("boardId")} for l in data])
        else:
            setattr(session, cache_key, None)
    result = getattr(session, cache_key, None)
    return result if result is not None else []


@mcp.tool()
def get_comments(board_id: str, card_id: str) -> list[dict]:
    """Get comments on a card."""
    _validate_id(board_id, "board_id")
    _validate_id(card_id, "card_id")
    session = _build_session()
    try:
        comments = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/cards/{card_id}/comments")
        if isinstance(comments, list):
            return [{"id": c.get("_id"), "text": c.get("comment"), "authorId": c.get("authorId")} for c in comments]
        return []
    except requests.exceptions.HTTPError as e:
        return [{"error": f"HTTP {e.response.status_code}"}]
    except requests.exceptions.ConnectionError as e:
        return [{"error": f"Connection failed: {e}"}]
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def add_comment(board_id: str, card_id: str, text: str) -> dict:
    """Add a comment to a card."""
    _validate_id(board_id, "board_id")
    _validate_id(card_id, "card_id")
    _validate_nonempty(text, "text")
    session = _build_session()
    try:
        comment = _http_post(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/cards/{card_id}/comments",
            json={"comment": text, "authorId": USER_ID},
        )
        if isinstance(comment, dict):
            return {"id": comment.get("_id")}
        return {"error": "Unexpected response from Wekan API"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_custom_fields(board_id: str) -> list[dict]:
    """Get custom fields defined on a board."""
    _validate_id(board_id, "board_id")
    session = _build_session()
    try:
        fields = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/custom-fields")
        if isinstance(fields, list):
            return [{"id": f.get("_id"), "name": f.get("name"), "type": f.get("type")} for f in fields]
        return []
    except requests.exceptions.HTTPError as e:
        return [{"error": f"HTTP {e.response.status_code}"}]
    except requests.exceptions.ConnectionError as e:
        return [{"error": f"Connection failed: {e}"}]
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def set_custom_field(board_id: str, list_id: str, card_id: str, field_id: str, value: str) -> dict:
    """Set a custom field value on a card."""
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    _validate_id(field_id, "field_id")
    _validate_nonempty(value, "value")
    session = _build_session()
    try:
        _http_post(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}/customFields/{field_id}",
            json={"_id": field_id, "value": value},
        )
        return {"fieldId": field_id, "value": value}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Card color tools (v0.1.2)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_allowed_colors() -> dict:
    """Get the list of allowed card colors for the target Wekan instance."""
    return {"colors": ALLOWED_COLORS}


@mcp.tool()
def get_card_color(board_id: str, list_id: str, card_id: str) -> dict:
    """Get the color of a card."""
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    session = _build_session()
    try:
        card = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
        if isinstance(card, dict):
            return {"color": card.get("color") or ""}
        return {"color": ""}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def set_card_color(board_id: str, list_id: str, card_id: str, color: str) -> dict:
    """Set the color of a card.

    Args:
        board_id: The board ID
        list_id: The list ID
        card_id: The card ID
        color: A valid Wekan color name from get_allowed_colors()
    """
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    _validate_color(color)
    session = _build_session()
    try:
        card = _http_put(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}",
            json={"color": color},
        )
        if isinstance(card, dict):
            return {"id": card.get("_id"), "color": card.get("color") or color}
        return {"id": card_id, "color": color}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_card_due_date(board_id: str, list_id: str, card_id: str) -> dict:
    """Get the due date (dueAt) of a card."""
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    session = _build_session()
    try:
        card = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
        if isinstance(card, dict):
            return {"dueAt": card.get("dueAt") or ""}
        return {"dueAt": ""}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def set_card_due_date(board_id: str, list_id: str, card_id: str, due_at: str) -> dict:
    """Set the due date of a card.

    Args:
        board_id: The board ID
        list_id: The list ID
        card_id: The card ID
        due_at: ISO 8601 datetime string (e.g., "2026-05-01T17:00:00.000Z")
               Use empty string to clear the due date.
    """
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    session = _build_session()
    try:
        card = _http_put(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}",
            json={"dueAt": due_at},
        )
        if isinstance(card, dict):
            return {"id": card.get("_id"), "dueAt": card.get("dueAt") or ""}
        return {"id": card_id, "dueAt": due_at}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_card_members(board_id: str, list_id: str, card_id: str) -> dict:
    """Get user IDs of members (involved users) on a card."""
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    session = _build_session()
    try:
        card = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
        if isinstance(card, dict):
            return {"members": card.get("members") or []}
        return {"members": []}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def set_card_members(board_id: str, list_id: str, card_id: str, member_ids: list[str]) -> dict:
    """Set members (involved users) on a card.

    Args:
        board_id: The board ID
        list_id: The list ID
        card_id: The card ID
        member_ids: List of user IDs to set as members
    """
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    if not isinstance(member_ids, list):
        return {"error": "member_ids must be a list of user IDs"}
    session = _build_session()
    try:
        card = _http_put(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}",
            json={"members": member_ids},
        )
        if isinstance(card, dict):
            return {"id": card.get("_id"), "members": card.get("members") or []}
        return {"id": card_id, "members": member_ids}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_card_assignees(board_id: str, list_id: str, card_id: str) -> dict:
    """Get user IDs of assignees on a card."""
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    session = _build_session()
    try:
        card = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
        if isinstance(card, dict):
            return {"assignees": card.get("assignees") or []}
        return {"assignees": []}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def set_card_assignees(board_id: str, list_id: str, card_id: str, assignee_ids: list[str]) -> dict:
    """Set assignees on a card.

    Note: Wekan API supports maximum 1 assignee. If more than 1 ID provided,
    returns error. Use an empty list to clear assignees.

    Args:
        board_id: The board ID
        list_id: The list ID
        card_id: The card ID
        assignee_ids: List of user IDs to set as assignees (max 1)
    """
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    if not isinstance(assignee_ids, list):
        return {"error": "assignee_ids must be a list of user IDs"}
    if len(assignee_ids) > 1:
        return {"error": "Wekan API supports maximum 1 assignee. Provided list has more than 1 ID."}
    session = _build_session()
    try:
        card = _http_put(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}",
            json={"assignees": assignee_ids},
        )
        if isinstance(card, dict):
            return {"id": card.get("_id"), "assignees": card.get("assignees") or []}
        return {"id": card_id, "assignees": assignee_ids}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Board label tools (v0.1.2)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_board_labels(board_id: str) -> list[dict]:
    """Get labels defined on a board."""
    _validate_id(board_id, "board_id")
    session = _build_session()
    try:
        board = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}")
        if isinstance(board, dict):
            labels = board.get("labels") or []
            return [
                {"id": lb.get("_id"), "name": lb.get("name", ""), "color": lb.get("color", "")}
                for lb in labels
            ]
        return []
    except requests.exceptions.HTTPError as e:
        return [{"error": f"HTTP {e.response.status_code}"}]
    except requests.exceptions.ConnectionError as e:
        return [{"error": f"Connection failed: {e}"}]
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_board_users(board_id: str) -> list[dict]:
    """Get all users on a board.

    Use the returned user IDs with set_card_members or set_card_assignees.
    """
    _validate_id(board_id, "board_id")
    session = _build_session()
    try:
        board = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}")
        if not isinstance(board, dict):
            return []
        board_members = board.get("members") or []
        if not board_members:
            return []
        result = []
        for m in board_members:
            user_id = m.get("userId")
            if not user_id:
                continue
            user_data = _http_get(session, f"{WEKAN_URL}/api/users/{user_id}")
            username = ""
            if isinstance(user_data, dict) and not user_data.get("error"):
                username = user_data.get("username") or ""
            result.append({
                "id": user_id,
                "username": username,
                "isAdmin": m.get("isAdmin", False),
                "isActive": m.get("isActive", False),
                "isWorker": m.get("isWorker", False),
            })
        return result
    except requests.exceptions.HTTPError as e:
        return [{"error": f"HTTP {e.response.status_code}"}]
    except requests.exceptions.ConnectionError as e:
        return [{"error": f"Connection failed: {e}"}]
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def add_board_label(board_id: str, name: str, color: str) -> dict:
    """Add a label to a board.

    Args:
        board_id: The board ID
        name: Label name (shown on cards)
        color: A valid Wekan color name from get_allowed_colors()
    """
    _validate_id(board_id, "board_id")
    _validate_nonempty(name, "name")
    _validate_color(color)
    session = _build_session()
    try:
        resp = _http_put(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/labels",
            json={"label": {"name": name, "color": color}},
        )
        if resp is None:
            return {"error": "Empty response — label may already exist"}
        if isinstance(resp, dict):
            return {"id": resp.get("_id") or str(resp), "name": name, "color": color}
        if isinstance(resp, str):
            return {"id": resp, "name": name, "color": color}
        return {"name": name, "color": color}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def edit_board_label(board_id: str, label_id: str, name: str = "", color: str = "") -> dict:
    """Edit a label on a board.

    Args:
        board_id: The board ID
        label_id: The label ID to edit
        name: New label name (leave empty to keep current)
        color: New color (leave empty to keep current)
    """
    _validate_id(board_id, "board_id")
    _validate_id(label_id, "label_id")
    if not name and not color:
        return {"error": "At least one of name or color must be provided"}
    if color:
        _validate_color(color)
    session = _build_session()
    try:
        board = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}")
        if not isinstance(board, dict):
            return {"error": "Failed to fetch board"}
        labels = board.get("labels") or []
        idx = next((i for i, lb in enumerate(labels) if lb.get("_id") == label_id), -1)
        if idx < 0:
            return {"error": f"Label {label_id} not found on board"}
        updated = labels.copy()
        updated[idx] = {**updated[idx], "_id": label_id, "name": name or updated[idx].get("name", ""), "color": color or updated[idx].get("color", "")}
        _http_put(session, f"{WEKAN_URL}/api/boards/{board_id}", json={"labels": updated})
        return {"id": label_id, "name": updated[idx]["name"], "color": updated[idx]["color"]}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Card label tools (v0.1.2)
# ---------------------------------------------------------------------------

@mcp.tool()
def add_card_label(board_id: str, list_id: str, card_id: str, label_id: str) -> dict:
    """Add a board label to a card.

    Args:
        board_id: The board ID
        list_id: The list ID
        card_id: The card ID
        label_id: The board label ID to add (from get_board_labels)
    """
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    _validate_id(label_id, "label_id")
    session = _build_session()
    try:
        card = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
        if not isinstance(card, dict):
            return {"error": "Failed to fetch card"}
        current_ids = card.get("labelIds") or []
        if label_id in current_ids:
            return {"id": card_id, "labelIds": current_ids}
        updated_ids = current_ids + [label_id]
        card = _http_put(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}",
            json={"labelIds": updated_ids},
        )
        return {"id": card_id, "labelIds": card.get("labelIds", []) if isinstance(card, dict) else updated_ids}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def remove_card_label(board_id: str, list_id: str, card_id: str, label_id: str) -> dict:
    """Remove a board label from a card.

    Args:
        board_id: The board ID
        list_id: The list ID
        card_id: The card ID
        label_id: The board label ID to remove
    """
    _validate_id(board_id, "board_id")
    _validate_id(list_id, "list_id")
    _validate_id(card_id, "card_id")
    _validate_id(label_id, "label_id")
    session = _build_session()
    try:
        card = _http_get(session, f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}")
        if not isinstance(card, dict):
            return {"error": "Failed to fetch card"}
        current_ids = card.get("labelIds") or []
        if label_id not in current_ids:
            return {"id": card_id, "labelIds": current_ids}
        updated_ids = [lid for lid in current_ids if lid != label_id]
        card = _http_put(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/lists/{list_id}/cards/{card_id}",
            json={"labelIds": updated_ids},
        )
        return {"id": card_id, "labelIds": card.get("labelIds", []) if isinstance(card, dict) else updated_ids}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Checklist item tools (v0.1.5)
# ---------------------------------------------------------------------------

@mcp.tool()
def update_checklist_item(board_id: str, card_id: str, checklist_id: str, item_id: str, is_finished: Optional[bool] = None, title: str = "") -> dict:
    """Update a checklist item's completion state or title.

    Args:
        board_id: The board ID
        card_id: The card ID
        checklist_id: The checklist ID
        item_id: The item ID
        is_finished: Set to True to check, False to uncheck (optional)
        title: New title text (optional)
    """
    _validate_id(board_id, "board_id")
    _validate_id(card_id, "card_id")
    _validate_id(checklist_id, "checklist_id")
    _validate_id(item_id, "item_id")
    if is_finished is None and not title:
        return {"error": "At least one of is_finished or title must be provided"}
    if title:
        _validate_nonempty(title, "title")
    session = _build_session()
    try:
        payload = {}
        if is_finished is not None:
            payload["isFinished"] = is_finished
        if title:
            payload["title"] = title
        result = _http_put(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/cards/{card_id}/checklists/{checklist_id}/items/{item_id}",
            json=payload,
        )
        if isinstance(result, dict):
            return {"id": result.get("_id"), "isFinished": is_finished, "title": title}
        return {"id": item_id, "isFinished": is_finished, "title": title}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection failed: {e}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def delete_checklist_item(board_id: str, card_id: str, checklist_id: str, item_id: str) -> bool:
    """Delete a checklist item."""
    _validate_id(board_id, "board_id")
    _validate_id(card_id, "card_id")
    _validate_id(checklist_id, "checklist_id")
    _validate_id(item_id, "item_id")
    session = _build_session()
    try:
        return _http_delete(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/cards/{card_id}/checklists/{checklist_id}/items/{item_id}",
        )
    except Exception:
        return False


@mcp.tool()
def delete_checklist(board_id: str, card_id: str, checklist_id: str) -> bool:
    """Delete a checklist from a card.

    Note: Editing checklist titles is not supported by the Wekan API.
    Delete and recreate the checklist manually if needed.
    """
    _validate_id(board_id, "board_id")
    _validate_id(card_id, "card_id")
    _validate_id(checklist_id, "checklist_id")
    session = _build_session()
    try:
        _http_delete(
            session,
            f"{WEKAN_URL}/api/boards/{board_id}/cards/{card_id}/checklists/{checklist_id}",
        )
        return True
    except Exception:
        return False


if __name__ == "__main__":
    mcp.run()