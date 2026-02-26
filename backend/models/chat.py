"""
Pydantic schemas for the chat API.
"""
from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    role:    Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Founder-level business query")
    history: list[HistoryMessage] = Field(
        default_factory=list,
        description="Previous conversation turns for follow-up context support",
    )


# ── SSE event shapes ──────────────────────────────────────────────────────────
# Every event the stream emits conforms to one of the types below.

class ToolCallEvent(BaseModel):
    type:  Literal["tool_call"] = "tool_call"
    name:  str
    args:  dict[str, Any] = Field(default_factory=dict)


class ToolResultEvent(BaseModel):
    type:         Literal["tool_result"] = "tool_result"
    name:         str
    item_count:   int = 0
    data_quality: dict[str, Any] = Field(default_factory=dict)


class MessageEvent(BaseModel):
    type:    Literal["message"] = "message"
    content: str


class ErrorEvent(BaseModel):
    type:    Literal["error"] = "error"
    message: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"


SSEEvent = ToolCallEvent | ToolResultEvent | MessageEvent | ErrorEvent | DoneEvent
