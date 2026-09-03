"""
Pydantic schemas for Mandi Recommendation requests and responses.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MandiRecommendationRequest(BaseModel):
    farmer_latitude: float = Field(..., ge=-90.0, le=90.0, description="Farmer GPS latitude", examples=[28.6139])
    farmer_longitude: float = Field(..., ge=-180.0, le=180.0, description="Farmer GPS longitude", examples=[77.2090])
    quantity_quintals: float = Field(..., gt=0.0, description="Quantity of produce in quintals", examples=[10.0])
    commodity: str = Field(default="Onion", description="Target crop commodity", examples=["Onion"])
    max_distance_km: Optional[float] = Field(default=None, gt=0.0, description="Optional maximum search radius in kilometers")
    transport_rate: float = Field(default=3.0, gt=0.0, description="Tariff rate (Rs / quintal / km)")
    farmer_facing: bool = Field(default=True, description="Enforces model quality gating and user safety alerts")


class MandiItemResponse(BaseModel):
    rank: int
    mandi: str
    state: str
    district: str
    distance_km: float
    current_price: float
    predicted_price: float
    expected_change: float
    expected_change_pct: float
    expected_direction: str
    horizon_days: int = 1
    transport_cost: float = 0.0
    market_fee: float = 0.0
    gross_revenue: float = 0.0
    total_cost: float = 0.0
    net_return: float = 0.0
    net_price_per_quintal: float = 0.0
    model_usage_status: str = "PRODUCTION_READY"
    model_reliability_score: float = 0.0
    model_quality_class: str = "STRONG"
    data_source: str = "CACHE"
    data_freshness_status: str = "CACHE_FRESH"
    data_age_days: int = 0
    historical_session_count: int = 0
    data_reliability_status: str = "READY"
    data_reliability_warning: str = ""
    risk_level: str = "LOW"
    confidence_score: float = 0.0
    market_condition: str = "NORMAL"
    recommendation_label: str = "ALTERNATIVE"
    reason: str = ""
    warning: str = ""
    lower_bound_80: float = 0.0
    upper_bound_80: float = 0.0
    # Backward-compatible fields
    transport_cost_per_quintal: Optional[float] = None
    total_transport_cost: Optional[float] = None
    market_fee_per_quintal: Optional[float] = None
    total_market_fee: Optional[float] = None
    expected_net_return: Optional[float] = None
    net_return_per_quintal: Optional[float] = None
    warning_reasons: Optional[List[str]] = None


class MandiRecommendationResponse(BaseModel):
    commodity: str
    farmer_latitude: float
    farmer_longitude: float
    quantity_quintals: float
    recommended_mandi: str
    total_mandis_evaluated: int
    overall_data_source: str = "CACHE"
    recommendations: List[MandiItemResponse]
    contract_metadata: Optional[Dict[str, Any]] = None
    # Backward-compatible fields
    data_source: Optional[str] = None
    farmer_location: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None

