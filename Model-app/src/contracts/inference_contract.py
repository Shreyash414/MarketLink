"""
Production Inference Contract & Integration Readiness Module.
Defines canonical, versioned, JSON-serializable intelligence contracts for backend consumption.
Enforces strict validation rules preventing accidental bypass of Task 7 or Task 8 safety gates.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple

from src.recommendation.schemas import MandiRecommendationItem, RecommendationResult
from src.utils.logger import logger

CONTRACT_VERSION = "1.0.0"

# Allowed Enum constants for public contract validation
VALID_DATA_SOURCES = {"LIVE", "CACHE", "NONE"}
VALID_FRESHNESS_STATUSES = {"LIVE_FRESH", "CACHE_FRESH", "CACHE_STALE", "NONE"}
VALID_RELIABILITY_STATUSES = {"READY", "BLOCKED", "CACHE_STALE", "INSUFFICIENT_HISTORY", "INVALID_DATA", "NONE"}
VALID_MODEL_USAGE_STATUSES = {"PRODUCTION_READY", "USABLE_WITH_WARNING", "RESEARCH_ONLY", "DISABLED", "MISSING"}
VALID_MODEL_QUALITY_CLASSES = {"STRONG", "ACCEPTABLE", "WEAK", "REJECT"}
VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}
VALID_RECOMMENDATION_LABELS = {"RECOMMENDED", "ALTERNATIVE"}


@dataclass
class ContractMetadata:
    schema_version: str = CONTRACT_VERSION
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    system_id: str = "SIH26132_AI_ENGINE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalInferenceItem:
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalRecommendationResponse:
    contract_metadata: ContractMetadata
    commodity: str
    farmer_latitude: float
    farmer_longitude: float
    quantity_quintals: float
    recommended_mandi: str
    total_mandis_evaluated: int
    overall_data_source: str
    recommendations: List[CanonicalInferenceItem]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_metadata": self.contract_metadata.to_dict(),
            "commodity": self.commodity,
            "farmer_latitude": self.farmer_latitude,
            "farmer_longitude": self.farmer_longitude,
            "quantity_quintals": self.quantity_quintals,
            "recommended_mandi": self.recommended_mandi,
            "total_mandis_evaluated": self.total_mandis_evaluated,
            "overall_data_source": self.overall_data_source,
            "recommendations": [rec.to_dict() for rec in self.recommendations]
        }

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def validate_inference_contract(response: CanonicalRecommendationResponse) -> Tuple[bool, str]:
    """
    Validation function verifying contract completeness, status enums, score ranges, and safety rules.
    Prevents bypassing Task 7 model-quality or Task 8 data-reliability gates.
    """
    if response is None:
        return False, "Canonical response object is null."

    if not response.commodity or not isinstance(response.commodity, str):
        return False, "Invalid or missing 'commodity' field."

    if response.quantity_quintals <= 0:
        return False, f"Invalid quantity_quintals: {response.quantity_quintals}"

    if not (-90.0 <= response.farmer_latitude <= 90.0) or not (-180.0 <= response.farmer_longitude <= 180.0):
        return False, "Invalid farmer GPS coordinates."

    if response.overall_data_source not in VALID_DATA_SOURCES:
        return False, f"Invalid overall_data_source: {response.overall_data_source}"

    for idx, rec in enumerate(response.recommendations, start=1):
        if rec.current_price < 0 or rec.predicted_price < 0:
            return False, f"Item {idx} ({rec.mandi}) contains negative prices."

        if not (0.0 <= rec.confidence_score <= 100.0):
            return False, f"Item {idx} ({rec.mandi}) confidence_score out of range [0, 100]: {rec.confidence_score}"

        if not (0.0 <= rec.model_reliability_score <= 100.0):
            return False, f"Item {idx} ({rec.mandi}) model_reliability_score out of range [0, 100]: {rec.model_reliability_score}"

        if rec.data_source not in VALID_DATA_SOURCES:
            return False, f"Item {idx} ({rec.mandi}) invalid data_source: {rec.data_source}"

        if rec.data_freshness_status not in VALID_FRESHNESS_STATUSES:
            return False, f"Item {idx} ({rec.mandi}) invalid data_freshness_status: {rec.data_freshness_status}"

        if rec.data_reliability_status not in VALID_RELIABILITY_STATUSES:
            return False, f"Item {idx} ({rec.mandi}) invalid data_reliability_status: {rec.data_reliability_status}"

        if rec.model_usage_status not in VALID_MODEL_USAGE_STATUSES:
            return False, f"Item {idx} ({rec.mandi}) invalid model_usage_status: {rec.model_usage_status}"

        if rec.model_quality_class not in VALID_MODEL_QUALITY_CLASSES:
            return False, f"Item {idx} ({rec.mandi}) invalid model_quality_class: {rec.model_quality_class}"

        if rec.risk_level not in VALID_RISK_LEVELS:
            return False, f"Item {idx} ({rec.mandi}) invalid risk_level: {rec.risk_level}"

        if rec.recommendation_label not in VALID_RECOMMENDATION_LABELS:
            return False, f"Item {idx} ({rec.mandi}) invalid recommendation_label: {rec.recommendation_label}"

        # Safety Gate Invariant 1: Task 7 Model Quality Gate
        if rec.model_usage_status in ("DISABLED", "RESEARCH_ONLY", "MISSING"):
            if rec.recommendation_label == "RECOMMENDED":
                return False, f"Safety Violation: Item {idx} ({rec.mandi}) with model status '{rec.model_usage_status}' cannot be labeled RECOMMENDED."

        # Safety Gate Invariant 2: Task 8 Data Reliability Gate
        if rec.data_reliability_status in ("BLOCKED", "INVALID_DATA", "INSUFFICIENT_HISTORY"):
            if rec.recommendation_label == "RECOMMENDED":
                return False, f"Safety Violation: Item {idx} ({rec.mandi}) with data reliability '{rec.data_reliability_status}' cannot be labeled RECOMMENDED."

    return True, "Canonical inference contract validation passed."


def build_canonical_recommendation(result: RecommendationResult) -> CanonicalRecommendationResponse:
    """
    Convert pipeline RecommendationResult into validated CanonicalRecommendationResponse contract.
    """
    meta = ContractMetadata()
    items: List[CanonicalInferenceItem] = []

    for rec in result.recommendations:
        item = CanonicalInferenceItem(
            rank=rec.rank,
            mandi=rec.mandi,
            state=rec.state,
            district=rec.district,
            distance_km=rec.distance_km,
            current_price=rec.current_price,
            predicted_price=rec.predicted_price,
            expected_change=rec.expected_change,
            expected_change_pct=rec.expected_change_pct,
            expected_direction=rec.expected_direction,
            horizon_days=1,
            transport_cost=rec.transport_cost,
            market_fee=rec.market_fee,
            gross_revenue=rec.gross_revenue,
            total_cost=rec.total_cost,
            net_return=rec.net_return,
            net_price_per_quintal=rec.net_price_per_quintal,
            model_usage_status=rec.model_usage_status,
            model_reliability_score=rec.model_reliability_score,
            model_quality_class=rec.model_quality_class,
            data_source=rec.data_source,
            data_freshness_status=rec.data_freshness_status,
            data_age_days=rec.data_age_days,
            historical_session_count=rec.historical_session_count,
            data_reliability_status=rec.data_reliability_status,
            data_reliability_warning=rec.data_reliability_warning,
            risk_level=rec.risk_level,
            confidence_score=rec.confidence_score,
            market_condition=rec.market_condition,
            recommendation_label=rec.recommendation_label,
            reason=rec.reason,
            warning=rec.warning,
            lower_bound_80=rec.lower_bound_80,
            upper_bound_80=rec.upper_bound_80,
        )
        items.append(item)

    canonical_res = CanonicalRecommendationResponse(
        contract_metadata=meta,
        commodity=result.commodity,
        farmer_latitude=result.farmer_latitude,
        farmer_longitude=result.farmer_longitude,
        quantity_quintals=result.quantity_quintals,
        recommended_mandi=result.recommended_mandi,
        total_mandis_evaluated=result.total_mandis_evaluated,
        overall_data_source=result.data_source,
        recommendations=items,
    )

    is_valid, reason = validate_inference_contract(canonical_res)
    if not is_valid:
        logger.warning(f"Canonical contract build produced validation error: {reason}")

    return canonical_res
