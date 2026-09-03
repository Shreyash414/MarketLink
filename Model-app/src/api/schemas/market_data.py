"""
Pydantic schemas for daily AGMARKNET mandi market prices.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class MandiPriceRecord(BaseModel):
    state: str
    district: str
    market: str
    commodity: str
    modal_price: float
    min_price: float
    max_price: float
    date: str


class MarketDataResponse(BaseModel):
    commodity: str
    data_source: str
    is_live: bool
    record_count: int
    records: List[MandiPriceRecord]
