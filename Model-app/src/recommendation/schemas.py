"""
Data schemas and output contracts for Mandi Recommendation Engine.
Used for structured API responses and downstream LLM / Ollama explanations.
"""
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MandiRecommendationItem:
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
    transport_cost: float
    market_fee: float
    gross_revenue: float
    total_cost: float
    net_return: float
    net_price_per_quintal: float
    risk_level: str
    confidence_score: float
    market_condition: str
    recommendation_label: str  # "RECOMMENDED" or "ALTERNATIVE"
    reason: str
    warning: str
    lower_bound_80: float = 0.0
    upper_bound_80: float = 0.0
    model_usage_status: str = "PRODUCTION_READY"
    model_reliability_score: float = 0.0
    model_quality_class: str = "STRONG"
    data_source: str = "CACHE"
    data_freshness_status: str = "CACHE_FRESH"
    data_age_days: int = 0
    historical_session_count: int = 0
    data_reliability_status: str = "READY"
    data_reliability_warning: str = ""



    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationResult:
    commodity: str
    farmer_latitude: float
    farmer_longitude: float
    quantity_quintals: float
    recommended_mandi: str
    total_mandis_evaluated: int
    data_source: str  # "LIVE" or "CACHE"
    recommendations: List[MandiRecommendationItem]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commodity": self.commodity,
            "farmer_latitude": self.farmer_latitude,
            "farmer_longitude": self.farmer_longitude,
            "quantity_quintals": self.quantity_quintals,
            "recommended_mandi": self.recommended_mandi,
            "total_mandis_evaluated": self.total_mandis_evaluated,
            "data_source": self.data_source,
            "recommendations": [rec.to_dict() for rec in self.recommendations]
        }

    def to_canonical_contract(self) -> Any:
        from src.contracts.inference_contract import build_canonical_recommendation
        return build_canonical_recommendation(self)

