"""
Agent service — Groq Llama 3.3 70B with tool calling.

Flow:
  1. Build message list (system + history + user query)
  2. Call Groq → inspect response
  3a. If tool_calls present → execute each tool (live Monday.com) → append results → repeat
  3b. If plain text → yield final message event → done
"""
from __future__ import annotations
import json
import logging
from typing import AsyncGenerator

from groq import Groq

from backend.config import get_settings
from backend.services.tools_service import TOOL_DEFINITIONS, execute_tool

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a Business Intelligence analyst for Skylark Drones — a drone services company \
operating across sectors such as Mining, Powerline, Agriculture, Construction, \
Oil & Gas, and Renewables.

You have real-time access to two Monday.com boards:
  • Deals Pipeline     — CRM data: deal stages, pipeline values, sectors, owners, close probability
  • Work Orders Tracker — Ops data: execution status, billing amounts, collections, work types

## Behaviour rules
- Always call a tool to fetch live data before answering — never guess numbers.
- Use query_deals_board     for pipeline / revenue / CRM questions.
- Use query_work_orders_board for operational / billing questions.
- Use cross_board_analysis   for cross-board or sector-wide questions.
- The tool response includes an owner_breakdown field — use it directly; \
  do NOT make additional per-owner API calls.
- Always surface data quality caveats (e.g. "Note: 52 % of deals are missing values").
- Format answers in markdown: tables for comparisons, bullets for lists, **bold** key numbers.
- Express currency in INR — format large amounts as Cr (crore = 10 M) or L (lakh = 100 K).
- If the query is ambiguous ask exactly ONE clarifying question before fetching data.

## INR formatting guide
  ≥ 1 Crore  → INR X.XX Cr
  ≥ 1 Lakh   → INR X.X L
  otherwise  → INR X,XXX
"""


def _make_groq_client() -> Groq:
    return Groq(api_key=get_settings().groq_api_key)


def _trim_for_context(result: dict, limit: int) -> dict:
    """
    Strip raw_items (large, redundant) and truncate items list to `limit` rows
    before sending as a tool result — keeps context window manageable.
    """
    out: dict = {}
    for k, v in result.items():
        if k == "raw_items":
            continue
        if k == "items" and isinstance(v, list):
            out[k] = v[:limit]
        else:
            out[k] = v
    return out


async def run_agent(
    user_query: str,
    history: list[dict],
) -> AsyncGenerator[dict, None]:
    """
    Async generator — yields plain dicts matching the SSE event shapes
    defined in backend/models/chat.py.

    Yields:
      {"type": "tool_call",   "name": ..., "args": ...}
      {"type": "tool_result", "name": ..., "item_count": ..., "data_quality": ...}
      {"type": "message",     "content": ...}
      {"type": "error",       "message": ...}
    """
    cfg    = get_settings()
    client = _make_groq_client()

    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_query})

    for iteration in range(cfg.agent_max_iterations):
        log.debug("Agent iteration %d | messages: %d", iteration + 1, len(messages))

        try:
            response = client.chat.completions.create(
                model=cfg.groq_model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                max_tokens=4096,
            )
        except Exception as exc:
            log.exception("Groq API call failed")
            yield {"type": "error", "message": f"LLM error: {exc}"}
            return

        choice = response.choices[0]
        msg    = choice.message

        # ── Terminal: plain text answer ───────────────────────────────────
        if not msg.tool_calls:
            log.info("Agent finished in %d iteration(s)", iteration + 1)
            yield {"type": "message", "content": msg.content or ""}
            return

        # ── Intermediate: one or more tool calls ──────────────────────────
        messages.append({
            "role":       "assistant",
            "content":    msg.content,
            "tool_calls": [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            fn_name = tc.function.name

            # Safely parse arguments — Groq can return null/malformed JSON
            try:
                fn_args = json.loads(tc.function.arguments or "{}")
                if not isinstance(fn_args, dict):
                    fn_args = {}
            except json.JSONDecodeError:
                fn_args = {}

            yield {"type": "tool_call", "name": fn_name, "args": fn_args}

            try:
                result     = await execute_tool(fn_name, fn_args)
                item_count = (
                    result.get("total_items")
                    or result.get("total_deals")
                    or result.get("total_work_orders")
                    or result.get("total_deals_analyzed", 0)
                )
                yield {
                    "type":         "tool_result",
                    "name":         fn_name,
                    "item_count":   item_count,
                    "data_quality": result.get("data_quality_notes", {}),
                }
                tool_content = json.dumps(
                    _trim_for_context(result, cfg.context_item_limit),
                    default=str,
                )
            except Exception as exc:
                log.exception("Tool execution failed: %s", fn_name)
                yield {"type": "error", "message": f"Tool error ({fn_name}): {exc}"}
                tool_content = json.dumps({"error": str(exc)})

            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      tool_content,
            })

    log.warning("Agent hit max iterations (%d) without a final answer", cfg.agent_max_iterations)
    yield {"type": "error", "message": "Agent reached maximum iterations without a final answer."}
