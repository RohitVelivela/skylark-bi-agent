"""
Deal — internal data model for a cleaned Deals Pipeline board item.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class Deal(BaseModel):
    id:                    Optional[str]   = None
    deal_name:             Optional[str]   = None
    owner_code:            Optional[str]   = None
    client_code:           Optional[str]   = None
    deal_status:           Optional[str]   = None
    deal_stage:            Optional[str]   = None
    deal_value:            Optional[float] = None
    closure_probability:   Optional[float] = None
    close_date:            Optional[str]   = None
    tentative_close_date:  Optional[str]   = None
    sector:                Optional[str]   = None
    product:               Optional[str]   = None
    created_date:          Optional[str]   = None
    data_quality_caveats:  list[str]       = []
