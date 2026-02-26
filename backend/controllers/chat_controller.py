"""
Chat controller — bridges the route layer and the agent service.
Responsibility: drive the agent, serialise every event into an SSE frame,
and guarantee the stream always ends with a 'done' event.
"""
from __future__ import annotations
import json
import logging
from typing import AsyncGenerator

from backend.models.chat import ChatRequest
from backend.services.agent_service import run_agent

log = logging.getLogger(__name__)


async def handle_chat(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Converts a ChatRequest into a stream of SSE-formatted strings.
    Each yielded string is a complete 'data: {...}\\n\\n' frame ready for the client.
    """
    history = [{"role": m.role, "content": m.content} for m in request.history]

    log.info("Chat request | query: %r | history_turns: %d",
             request.message[:80], len(history))

    try:
        async for event in run_agent(request.message, history):
            yield _to_sse(event)
    except Exception as exc:
        log.exception("Unhandled error in chat controller")
        yield _to_sse({"type": "error", "message": str(exc)})
    finally:
        yield _to_sse({"type": "done"})


def _to_sse(payload: dict) -> str:
    """Serialise a dict to a Server-Sent Events data frame."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
