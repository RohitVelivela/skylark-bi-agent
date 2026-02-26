"""
Monday.com GraphQL service.
Every public function makes a fresh HTTP call — no caching, no preloading (per spec).
Uses httpx.AsyncClient for non-blocking I/O.
"""
from __future__ import annotations
import logging
import httpx
from backend.config import get_settings

log = logging.getLogger(__name__)

_MONDAY_URL = "https://api.monday.com/v2"

_ITEMS_QUERY = """
query ($boardId: [ID!]!, $limit: Int!) {
  boards(ids: $boardId) {
    items_page(limit: $limit) {
      items {
        id
        name
        column_values {
          id text value
          column { title type }
        }
      }
    }
  }
}
"""


def _auth_headers() -> dict[str, str]:
    cfg = get_settings()
    return {
        "Authorization": f"Bearer {cfg.monday_api_token}",
        "Content-Type":  "application/json",
        "API-Version":   "2024-01",
    }


async def fetch_board_items(board_id: str) -> list[dict]:
    """
    Fetch all items from a Monday.com board.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    cfg = get_settings()
    payload = {
        "query": _ITEMS_QUERY,
        "variables": {
            "boardId": [str(board_id)],
            "limit":   cfg.tool_item_limit,
        },
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        log.debug("Fetching items from board %s", board_id)
        resp = await client.post(_MONDAY_URL, json=payload, headers=_auth_headers())
        resp.raise_for_status()

    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"Monday.com API error: {data['errors']}")

    boards = data.get("data", {}).get("boards", [])
    if not boards:
        log.warning("Board %s returned no data", board_id)
        return []

    items = boards[0].get("items_page", {}).get("items", [])
    log.info("Board %s → %d items fetched", board_id, len(items))
    return items


async def fetch_deals() -> list[dict]:
    return await fetch_board_items(get_settings().deals_board_id)


async def fetch_work_orders() -> list[dict]:
    return await fetch_board_items(get_settings().work_orders_board_id)
