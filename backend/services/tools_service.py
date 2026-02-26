"""
Tools service — Groq-compatible tool schemas and async executor.
Each tool fetches live data from Monday.com, normalizes it, and returns
an aggregated summary dict that is safe to pass as a tool result to the LLM.
"""
from __future__ import annotations
import logging
from backend.services.monday_service import fetch_deals, fetch_work_orders
from backend.utils.normalizer import clean_deal, clean_work_order, normalize_sector

log = logging.getLogger(__name__)

# Values the LLM sometimes passes to mean "no filter"
_EMPTY_FILTER_VALUES = {"", "all", "any", "none", "n/a", "*", "null", "undefined"}


def _is_active_filter(value) -> bool:
    return bool(value) and str(value).strip().lower() not in _EMPTY_FILTER_VALUES


# ── Tool schemas (OpenAI-compatible — Groq uses same spec) ────────────────────

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "query_deals_board",
            "description": (
                "Fetch live deal and pipeline data from Monday.com. "
                "Use for: pipeline health, revenue totals, deal stage breakdown, "
                "sector performance, owner rankings, closure probability analysis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sector":      {"type": "string", "description": "Sector filter e.g. Mining, Powerline. Omit for all."},
                    "deal_stage":  {"type": "string", "description": "Partial match on deal stage. Omit for all."},
                    "deal_status": {"type": "string", "description": "Open | Closed Won | Closed Lost | On Hold. Omit for all."},
                    "owner_code":  {"type": "string", "description": "Owner code e.g. OWNER_001. Omit for all."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_work_orders_board",
            "description": (
                "Fetch live work order data from Monday.com. "
                "Use for: execution status, billing amounts, collection tracking, "
                "work type breakdown, delivery timelines."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sector":           {"type": "string", "description": "Sector filter. Omit for all."},
                    "execution_status": {"type": "string", "description": "Completed | In Progress | Not Started | On Hold. Omit for all."},
                    "nature_of_work":   {"type": "string", "description": "One time Project | Monthly Contract | Proof of Concept. Omit for all."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cross_board_analysis",
            "description": (
                "Query both boards and correlate data by deal name. "
                "Use for: revenue vs billed comparison, pipeline-to-execution tracking, "
                "full sector overview across deals and work orders."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "enum": ["revenue_vs_billed", "pipeline_to_execution", "sector_overview"],
                        "description": "The type of cross-board analysis to perform.",
                    },
                    "sector": {"type": "string", "description": "Optional sector scope."},
                },
                "required": ["analysis_type"],
            },
        },
    },
]


# ── Filtering ─────────────────────────────────────────────────────────────────

def _apply_filters(items: list[dict], filters: dict) -> list[dict]:
    result = items

    if _is_active_filter(filters.get("sector")):
        target = normalize_sector(filters["sector"])
        result = [i for i in result if normalize_sector(i.get("sector")) == target]

    if _is_active_filter(filters.get("deal_stage")):
        kw = filters["deal_stage"].lower()
        result = [i for i in result if i.get("deal_stage") and kw in i["deal_stage"].lower()]

    if _is_active_filter(filters.get("deal_status")):
        kw = filters["deal_status"].lower()
        result = [i for i in result if i.get("deal_status") and kw in i["deal_status"].lower()]

    if _is_active_filter(filters.get("owner_code")):
        kw = filters["owner_code"].lower()
        result = [i for i in result if i.get("owner_code") and kw in i["owner_code"].lower()]

    if _is_active_filter(filters.get("execution_status")):
        kw = filters["execution_status"].lower()
        result = [i for i in result if i.get("execution_status") and kw in i["execution_status"].lower()]

    if _is_active_filter(filters.get("nature_of_work")):
        kw = filters["nature_of_work"].lower()
        result = [i for i in result if i.get("nature_of_work") and kw in i["nature_of_work"].lower()]

    return result


# ── Async executor ────────────────────────────────────────────────────────────

async def execute_tool(name: str, args: dict) -> dict:
    """Dispatch a tool call and return a serialisable result dict."""
    log.info("Executing tool: %s | args: %s", name, args)

    if name == "query_deals_board":
        raw      = await fetch_deals()
        cleaned  = [clean_deal(item) for item in raw]
        filtered = _apply_filters(cleaned, args)
        return _summarise_deals(filtered, args)

    if name == "query_work_orders_board":
        raw      = await fetch_work_orders()
        cleaned  = [clean_work_order(item) for item in raw]
        filtered = _apply_filters(cleaned, args)
        return _summarise_work_orders(filtered, args)

    if name == "cross_board_analysis":
        deals_raw, wo_raw = await fetch_deals(), await fetch_work_orders()
        deals       = [clean_deal(i) for i in deals_raw]
        work_orders = [clean_work_order(i) for i in wo_raw]

        if _is_active_filter(args.get("sector")):
            t = normalize_sector(args["sector"])
            deals       = [d for d in deals       if normalize_sector(d.get("sector")) == t]
            work_orders = [w for w in work_orders if normalize_sector(w.get("sector")) == t]

        return _cross_analysis(deals, work_orders, args.get("analysis_type", "sector_overview"))

    raise ValueError(f"Unknown tool: {name!r}")


# ── Summary builders ──────────────────────────────────────────────────────────

def _summarise_deals(items: list[dict], filters: dict) -> dict:
    total       = len(items)
    with_value  = [i for i in items if i["deal_value"] is not None]
    total_value = sum(i["deal_value"] for i in with_value)

    stages:  dict[str, int]  = {}
    sectors: dict[str, dict] = {}
    owners:  dict[str, dict] = {}

    for i in items:
        # stage breakdown
        s = i.get("deal_stage") or "Unknown"
        stages[s] = stages.get(s, 0) + 1

        # sector breakdown
        sec = i.get("sector") or "Unknown"
        if sec not in sectors:
            sectors[sec] = {"count": 0, "value": 0.0, "value_count": 0}
        sectors[sec]["count"] += 1
        if i["deal_value"] is not None:
            sectors[sec]["value"]       += i["deal_value"]
            sectors[sec]["value_count"] += 1

        # owner breakdown — avoids model needing multiple API calls
        ow = i.get("owner_code") or "Unknown"
        if ow not in owners:
            owners[ow] = {"deal_count": 0, "value": 0.0}
        owners[ow]["deal_count"] += 1
        if i["deal_value"] is not None:
            owners[ow]["value"] += i["deal_value"]

    owner_breakdown = dict(
        sorted(owners.items(), key=lambda x: x[1]["deal_count"], reverse=True)
    )
    top_5 = sorted(with_value, key=lambda x: x["deal_value"], reverse=True)[:5]

    return {
        "board":                  "Deals Pipeline",
        "filters_applied":        filters,
        "total_items":            total,
        "deals_with_value":       len(with_value),
        "total_pipeline_value_inr": round(total_value, 2),
        "open_deals":             sum(1 for i in items if i.get("deal_status") == "Open"),
        "closed_won":             sum(1 for i in items if i.get("deal_status") == "Closed Won"),
        "closed_lost":            sum(1 for i in items if i.get("deal_status") == "Closed Lost"),
        "stage_breakdown":        stages,
        "sector_breakdown":       sectors,
        "owner_breakdown":        owner_breakdown,
        "top_5_deals_by_value":   [
            {"deal_name": d["deal_name"], "value": d["deal_value"],
             "stage": d["deal_stage"], "sector": d["sector"], "status": d["deal_status"]}
            for d in top_5
        ],
        "data_quality_notes": {
            "value_coverage":      f"{len(with_value)}/{total} deals have value data",
            "missing_close_dates": sum(
                1 for i in items
                if not i.get("close_date") and not i.get("tentative_close_date")
            ),
            "total_quality_flags": sum(len(i["data_quality_caveats"]) for i in items),
        },
        "raw_items": items,
    }


def _summarise_work_orders(items: list[dict], filters: dict) -> dict:
    total          = len(items)
    with_amount    = [i for i in items if i["amount_excl_gst"]       is not None]
    with_billed    = [i for i in items if i["billed_value_excl_gst"] is not None]
    with_collected = [i for i in items if i["collected_amount"]       is not None]

    statuses:   dict[str, int]  = {}
    sectors:    dict[str, dict] = {}
    work_types: dict[str, int]  = {}

    for i in items:
        s = i.get("execution_status") or "Unknown"
        statuses[s] = statuses.get(s, 0) + 1

        sec = i.get("sector") or "Unknown"
        if sec not in sectors:
            sectors[sec] = {"count": 0, "amount": 0.0, "billed": 0.0}
        sectors[sec]["count"] += 1
        if i["amount_excl_gst"]       is not None: sectors[sec]["amount"]  += i["amount_excl_gst"]
        if i["billed_value_excl_gst"] is not None: sectors[sec]["billed"]  += i["billed_value_excl_gst"]

        wt = i.get("nature_of_work") or "Unknown"
        work_types[wt] = work_types.get(wt, 0) + 1

    return {
        "board":                    "Work Orders Tracker",
        "filters_applied":          filters,
        "total_items":              total,
        "total_contract_value_inr": round(sum(i["amount_excl_gst"]       for i in with_amount),    2),
        "total_billed_value_inr":   round(sum(i["billed_value_excl_gst"] for i in with_billed),    2),
        "total_collected_inr":      round(sum(i["collected_amount"]       for i in with_collected), 2),
        "coverage": {
            "amount":     f"{len(with_amount)}/{total}",
            "billing":    f"{len(with_billed)}/{total}",
            "collection": f"{len(with_collected)}/{total}",
        },
        "execution_status_breakdown": statuses,
        "sector_breakdown":           sectors,
        "work_type_breakdown":         work_types,
        "data_quality_notes": {
            "total_quality_flags":   sum(len(i["data_quality_caveats"]) for i in items),
            "collection_data_sparse": len(with_collected) < total * 0.1,
        },
        "raw_items": items,
    }


def _cross_analysis(deals: list[dict], work_orders: list[dict], analysis_type: str) -> dict:
    wo_index: dict[str, list] = {}
    for wo in work_orders:
        key = (wo.get("deal_name") or "").strip().lower()
        if key:
            wo_index.setdefault(key, []).append(wo)

    if analysis_type == "revenue_vs_billed":
        rows = []
        for deal in deals:
            key = (deal.get("deal_name") or "").strip().lower()
            wos = wo_index.get(key, [])
            billed = sum(w["billed_value_excl_gst"] or 0 for w in wos)
            if deal["deal_value"] is not None or billed > 0:
                rows.append({
                    "deal_name":       deal.get("deal_name"),
                    "sector":          deal.get("sector"),
                    "pipeline_value":  deal.get("deal_value"),
                    "billed_value":    billed or None,
                    "work_order_count": len(wos),
                })
        return {
            "analysis_type":           "revenue_vs_billed",
            "total_deals_analyzed":    len(deals),
            "total_wo_analyzed":       len(work_orders),
            "deals_with_work_orders":  sum(1 for r in rows if r["work_order_count"] > 0),
            "items":                   rows,
        }

    if analysis_type == "pipeline_to_execution":
        rows = [
            {
                "deal_name":            d.get("deal_name"),
                "deal_stage":           d.get("deal_stage"),
                "deal_status":          d.get("deal_status"),
                "sector":               d.get("sector"),
                "has_work_order":       bool(wo_index.get((d.get("deal_name") or "").strip().lower())),
                "work_order_statuses":  [
                    w.get("execution_status")
                    for w in wo_index.get((d.get("deal_name") or "").strip().lower(), [])
                ],
            }
            for d in deals
        ]
        return {
            "analysis_type":         "pipeline_to_execution",
            "total_deals":           len(deals),
            "deals_converted_to_wo": sum(1 for r in rows if r["has_work_order"]),
            "items":                 rows,
        }

    # sector_overview (default)
    sectors: dict[str, dict] = {}
    for d in deals:
        sec = d.get("sector") or "Unknown"
        if sec not in sectors:
            sectors[sec] = {"pipeline_deals": 0, "pipeline_value": 0.0,
                            "work_orders": 0, "billed_value": 0.0, "open_deals": 0}
        sectors[sec]["pipeline_deals"] += 1
        if d.get("deal_value"):       sectors[sec]["pipeline_value"] += d["deal_value"]
        if d.get("deal_status") == "Open": sectors[sec]["open_deals"] += 1

    for wo in work_orders:
        sec = wo.get("sector") or "Unknown"
        if sec not in sectors:
            sectors[sec] = {"pipeline_deals": 0, "pipeline_value": 0.0,
                            "work_orders": 0, "billed_value": 0.0, "open_deals": 0}
        sectors[sec]["work_orders"] += 1
        if wo.get("billed_value_excl_gst"): sectors[sec]["billed_value"] += wo["billed_value_excl_gst"]

    return {
        "analysis_type":     "sector_overview",
        "total_deals":       len(deals),
        "total_work_orders": len(work_orders),
        "sectors":           sectors,
    }
