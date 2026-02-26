"""
Chat routes — HTTP boundary only.
No business logic lives here; everything is delegated to the controller.
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.models.chat import ChatRequest
from backend.controllers.chat_controller import handle_chat

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post(
    "/chat",
    summary="Stream a BI agent response",
    description=(
        "Send a natural-language business query and receive a Server-Sent Events stream. "
        "Events: tool_call → tool_result → message (final answer) → done."
    ),
    response_description="SSE stream of agent events",
)
async def chat(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        handle_chat(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )
