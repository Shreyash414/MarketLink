"""
Pydantic schemas for direct single-market price forecasting.
"""
from typing import Dict, Optional
from pydantic import BaseModel, Field


class SinglePredictionRequest(BaseModel):
    market: str = Field(..., description="Target mandi name", examples=["Bareilly"])
    commodity: str = Field(default="Onion", description="Agricultural commodity", examples=["Onion"])
    current_price: float = Field(..., gt=0.0, description="Current observed price in Rs / quintal", examples=[1850.0])
    features: Dict[str, float] = Field(..., description="Key-value mapping of V3 inference features")
    date: Optional[str] = Field(default=None, description="ISO date of current observation")
    farmer_facing: bool = Field(default=True, description="Whether request enforces model quality gating")


class SinglePredictionResponse(BaseModel):
    market: str
    commodity: str
    current_price: float
    predicted_price: float
    expected_change: float
    expected_change_pct: float
    expected_direction: str
    usage_status: str
    reliability_score: float
    quality_class: str
    data_source: str
