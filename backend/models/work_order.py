"""
WorkOrder — internal data model for a cleaned Work Orders Tracker board item.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class WorkOrder(BaseModel):
    id:                    Optional[str]   = None
    deal_name:             Optional[str]   = None
    customer_code:         Optional[str]   = None
    serial_number:         Optional[str]   = None
    nature_of_work:        Optional[str]   = None
    execution_status:      Optional[str]   = None
    sector:                Optional[str]   = None
    type_of_work:          Optional[str]   = None
    amount_excl_gst:       Optional[float] = None
    billed_value_excl_gst: Optional[float] = None
    collected_amount:      Optional[float] = None
    po_date:               Optional[str]   = None
    delivery_date:         Optional[str]   = None
    invoice_status:        Optional[str]   = None
    wo_status:             Optional[str]   = None
    bd_personnel:          Optional[str]   = None
    ar_priority:           Optional[str]   = None
    data_quality_caveats:  list[str]       = []
