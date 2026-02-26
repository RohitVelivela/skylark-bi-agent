"""
Data normalizer — cleans raw Monday.com item dicts into typed, consistent values.
Handles every messy pattern found in the source data:
  - 50%+ missing numeric fields
  - Mixed date formats (DD/MM/YY, ISO, Excel serial)
  - Sector name variants (power line / Powerline / POWERLINE)
  - INR currency strings with commas, symbols, lakh/crore suffixes
"""
from __future__ import annotations
import re
import logging
from datetime import datetime, timedelta
from typing import Optional

log = logging.getLogger(__name__)

# ── Sector canonical map ──────────────────────────────────────────────────────
_SECTOR_MAP: dict[str, str] = {
    "powerline": "Powerline", "power line": "Powerline",
    "power lines": "Powerline", "power-line": "Powerline",
    "mining": "Mining",
    "agriculture": "Agriculture", "agri": "Agriculture",
    "oil & gas": "Oil & Gas", "oil and gas": "Oil & Gas", "oil&gas": "Oil & Gas",
    "construction": "Construction",
    "infrastructure": "Infrastructure", "infra": "Infrastructure",
    "solar": "Solar", "renewables": "Renewables", "renewable": "Renewables",
    "telecom": "Telecom", "railway": "Railway", "railways": "Railway",
    "defense": "Defense", "defence": "Defense",
    "urban": "Urban", "real estate": "Real Estate",
    "tender": "Tender", "aviation": "Aviation", "dsp": "DSP",
}

# ── Deal status canonical map ─────────────────────────────────────────────────
_DEAL_STATUS_MAP: dict[str, str] = {
    "open": "Open", "active": "Open",
    "closed won": "Closed Won", "won": "Closed Won", "closed - won": "Closed Won",
    "closed loss": "Closed Lost", "closed lost": "Closed Lost",
    "lost": "Closed Lost", "closed - lost": "Closed Lost",
    "on hold": "On Hold", "hold": "On Hold",
}

# ── Execution status canonical map ────────────────────────────────────────────
_EXEC_STATUS_MAP: dict[str, str] = {
    "completed": "Completed", "complete": "Completed", "done": "Completed",
    "in progress": "In Progress", "ongoing": "In Progress",
    "not started": "Not Started", "pending": "Not Started",
    "executed until current month": "Ongoing (Monthly)",
    "on hold": "On Hold", "cancelled": "Cancelled", "canceled": "Cancelled",
}

_NULL_STRINGS = {"", "nan", "none", "n/a", "-", "null"}

_DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y",
    "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y",
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
]


def _is_null(value: Optional[str]) -> bool:
    return value is None or str(value).strip().lower() in _NULL_STRINGS


# ── Public normalizers ────────────────────────────────────────────────────────

def normalize_sector(raw: Optional[str]) -> Optional[str]:
    if _is_null(raw):
        return None
    key = str(raw).strip().lower()
    return _SECTOR_MAP.get(key, str(raw).strip().title())


def normalize_deal_status(raw: Optional[str]) -> Optional[str]:
    if _is_null(raw):
        return None
    return _DEAL_STATUS_MAP.get(str(raw).strip().lower(), str(raw).strip())


def normalize_execution_status(raw: Optional[str]) -> Optional[str]:
    if _is_null(raw):
        return None
    return _EXEC_STATUS_MAP.get(str(raw).strip().lower(), str(raw).strip())


def parse_currency(raw: Optional[str]) -> Optional[float]:
    """Parse INR strings — handles commas, symbols, lakh/crore multipliers."""
    if _is_null(raw):
        return None
    s = re.sub(r"[,\s]", "", str(raw).strip())
    s = re.sub(r"(?i)inr|rs\.?", "", s).strip()

    multiplier = 1.0
    if s.lower().endswith("cr"):
        multiplier, s = 1e7, s[:-2]
    elif s.lower().endswith("lakh"):
        multiplier, s = 1e5, re.sub(r"(?i)lakh$", "", s)
    elif s.lower().endswith("l") and not s.lower().endswith("null"):
        multiplier, s = 1e5, s[:-1]

    try:
        return float(s) * multiplier
    except (ValueError, TypeError):
        log.debug("Could not parse currency value: %r", raw)
        return None


def parse_number(raw: Optional[str]) -> Optional[float]:
    if _is_null(raw):
        return None
    s = str(raw).strip().replace(",", "").rstrip("%")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_date(raw: Optional[str]) -> Optional[str]:
    """Try multiple date formats; handles Excel serial numbers too."""
    if _is_null(raw):
        return None
    s = str(raw).strip()

    # Excel serial date
    try:
        serial = float(s)
        if 20_000 < serial < 60_000:
            return (datetime(1899, 12, 30) + timedelta(days=serial)).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue

    log.debug("Could not parse date value: %r", raw)
    return None


# ── Column helper ─────────────────────────────────────────────────────────────

def _col(item: dict, title: str) -> Optional[str]:
    """Extract the text value of a column by its title (case-insensitive)."""
    for cv in item.get("column_values", []):
        if cv.get("column", {}).get("title", "").strip().lower() == title.lower():
            return cv.get("text") or None
    return None


# ── Item cleaners ─────────────────────────────────────────────────────────────

def clean_deal(item: dict) -> dict:
    """Map a raw Monday.com Deals item → clean dict with data quality caveats."""
    deal_value  = parse_currency(_col(item, "Masked Deal value"))
    probability = parse_number(_col(item, "Closure Probability"))
    close_date  = parse_date(_col(item, "Close Date (A)"))
    tentative   = parse_date(_col(item, "Tentative Close Date"))
    created     = parse_date(_col(item, "Created Date"))
    sector      = normalize_sector(_col(item, "Sector/service"))
    status      = normalize_deal_status(_col(item, "Deal Status"))

    caveats: list[str] = []
    if deal_value  is None: caveats.append("deal_value_missing")
    if probability is None: caveats.append("probability_missing")
    if not close_date and not tentative: caveats.append("close_date_missing")

    return {
        "id":                   item.get("id"),
        "deal_name":            item.get("name"),
        "owner_code":           _col(item, "Owner code"),
        "client_code":          _col(item, "Client Code"),
        "deal_status":          status,
        "deal_stage":           _col(item, "Deal Stage"),
        "deal_value":           deal_value,
        "closure_probability":  probability,
        "close_date":           close_date,
        "tentative_close_date": tentative,
        "sector":               sector,
        "product":              _col(item, "Product deal"),
        "created_date":         created,
        "data_quality_caveats": caveats,
    }


def clean_work_order(item: dict) -> dict:
    """Map a raw Monday.com Work Orders item → clean dict with data quality caveats."""
    amount    = parse_currency(_col(item, "Amount in Rupees (Excl of GST) (Masked)"))
    billed    = parse_currency(_col(item, "Billed Value in Rupees (Excl of GST.) (Masked)"))
    collected = parse_currency(_col(item, "Collected Amount in Rupees (Incl of GST.) (Masked)"))
    sector    = normalize_sector(_col(item, "Sector"))
    exec_st   = normalize_execution_status(_col(item, "Execution Status"))

    caveats: list[str] = []
    if amount    is None: caveats.append("amount_missing")
    if billed    is None: caveats.append("billed_value_missing")
    if collected is None: caveats.append("collected_amount_missing")
    if exec_st   is None: caveats.append("execution_status_missing")

    return {
        "id":                    item.get("id"),
        "deal_name":             item.get("name"),
        "customer_code":         _col(item, "Customer Name Code"),
        "serial_number":         _col(item, "Serial #"),
        "nature_of_work":        _col(item, "Nature of Work"),
        "execution_status":      exec_st,
        "sector":                sector,
        "type_of_work":          _col(item, "Type of Work"),
        "amount_excl_gst":       amount,
        "billed_value_excl_gst": billed,
        "collected_amount":      collected,
        "po_date":               parse_date(_col(item, "Date of PO/LOI")),
        "delivery_date":         parse_date(_col(item, "Data Delivery Date")),
        "invoice_status":        _col(item, "Invoice Status"),
        "wo_status":             _col(item, "WO Status (billed)"),
        "bd_personnel":          _col(item, "BD/KAM Personnel code"),
        "ar_priority":           _col(item, "AR Priority account"),
        "data_quality_caveats":  caveats,
    }
