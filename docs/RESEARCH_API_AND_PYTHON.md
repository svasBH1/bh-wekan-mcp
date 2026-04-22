# Research: Wekan REST API & Python Integration

**Date:** 2026-04-20
**Status:** Completed (Phase 1)

## Findings Overview

### 1. Wekan REST API
Wekan provides a comprehensive REST API for managing boards, lists, and cards.
- **Documentation:** [wekan/docs/API/REST-API.md](https://github.com/wekan/wekan/blob/main/docs/API/REST-API.md)
- **Interactive UI:** Usually found at `https://<your-wekan-domain>/api/docs` (Swagger/OpenAPI).
- **Authentication:**
    - Uses Bearer Tokens.
    - Login: `POST /users/login` with `{"username": "...", "password": "..."}`.
    - Header: `Authorization: Bearer <token>`.

### 2. Python Client Options
- **`python-wekan` (Recommended):** A high-level library that wraps the API into Pythonic objects (Boards, Lists, Cards).
    - `pip install python-wekan`
    - Good for clean, readable MCP tool implementations.
- **`api.py` (Official Reference):** A standalone script in the Wekan repo. Excellent for understanding the raw JSON structures and edge cases.
    - [Source on GitHub](https://github.com/wekan/wekan/blob/main/api.py)

### 3. Key Endpoints for MCP Tools
| MCP Tool Intent | HTTP Method | Endpoint |
| :--- | :--- | :--- |
| `list_boards` | GET | `/api/boards` |
| `get_lists` | GET | `/api/boards/{boardId}/lists` |
| `add_card` | POST | `/api/boards/{boardId}/lists/{listId}/cards` |
| `search_cards` | GET | `/api/boards/{boardId}/lists/{listId}/cards` (Filterable) |
| `add_comment` | POST | `/api/boards/{boardId}/cards/{cardId}/comments` |

## Recommendations for MCP Development
1. **Use the MCP Python SDK:** It is well-documented and integrates easily with `python-wekan`.
2. **Environment Configuration:** Store the Wekan URL, Username, and Password in a `.env` file during local testing.
3. **Handle Snap v7.60 Limitations:**
    - Some v8.x features (Gantt, numeric sum in headers) may not be available in v7.60.
    - Stick to core CRUD (Create, Read, Update, Delete) operations first.

## Token Generation (Updated 2026-04-21)

**Finding:** There is no separate token generation endpoint in Wekan v7.60.
The token is returned directly from `POST /users/login`.

Login response format:
```json
{
  "id": "user id",
  "token": "Bearer token string",
  "tokenExpires": "ISO encoded date string"
}
```

Previous attempts at `/api/users/{id}/token`, `/api/users/me/token`, `/api/users/{id}/tokens` all returned 405 because those endpoints do not exist.

## Open Questions
- Does v7.60 support the new "Global Search" API endpoints?
- Are custom field values accessible via the standard `get_card` endpoint in v7.60?
