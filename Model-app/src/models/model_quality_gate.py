"""
Model Quality Gate Module.
Centralized, deterministic model quality gating layer for production inference & mandi recommendation.
Enforces Task 6 model quality audit decisions:
  - PRODUCTION_READY    : Full deployment; safe for farmer-facing recommendation
  - USABLE_WITH_WARNING : Allowed for farmer recommendation with structured UI warning
  - RESEARCH_ONLY       : Blocked for farmer-facing recommendation; allowed ONLY in dev/research mode
  - DISABLED / MISSING  : Blocked completely for all inference & recommendations
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.config.model_registry import get_registered_model
from src.utils.logger import logger

# Usage status constants
STATUS_PRODUCTION_READY = "PRODUCTION_READY"
STATUS_USABLE_WITH_WARNING = "USABLE_WITH_WARNING"
STATUS_RESEARCH_ONLY = "RESEARCH_ONLY"
STATUS_DISABLED = "DISABLED"
STATUS_MISSING = "MISSING"

# Quality class constants
QUALITY_STRONG = "STRONG"
QUALITY_ACCEPTABLE = "ACCEPTABLE"
QUALITY_WEAK = "WEAK"
QUALITY_REJECT = "REJECT"


@dataclass
class ModelQualityGateResult:
    commodity: str
    market: str
    allowed: bool
    usage_status: str
    reliability_score: float
    quality_class: str
    warning: str
    reason: str


def get_model_quality_metadata(commodity: str, market: str) -> Dict[str, Any]:
    """
    Retrieve authoritative Task 6 model quality & usage metadata from ModelRegistry.
    """
    reg_info = get_registered_model(commodity=commodity, market=market)
    if not reg_info:
        return {
            "commodity": commodity.strip(),
            "market": market.strip(),
            "usage_status": STATUS_MISSING,
            "reliability_score": 0.0,
            "quality_class": QUALITY_REJECT,
            "warning": f"No trained model registered for {commodity} / {market}.",
        }

    usage_status = reg_info.get("usage_status", STATUS_DISABLED)
    reliability_score = float(reg_info.get("reliability_score", 0.0))
    quality_class = reg_info.get("quality_class", QUALITY_WEAK)

    warning = ""
    if usage_status == STATUS_USABLE_WITH_WARNING:
        warning = f"Model for {commodity} / {market} has moderate historical error; predictions carry higher uncertainty."
    elif usage_status == STATUS_RESEARCH_ONLY:
        warning = f"Model for {commodity} / {market} is unapproved for farmer use (RESEARCH_ONLY)."
    elif usage_status == STATUS_DISABLED:
        warning = f"Model for {commodity} / {market} is hard disabled due to poor historical fit (DISABLED)."

    return {
        "commodity": reg_info.get("commodity", commodity),
        "market": reg_info.get("market", market),
        "usage_status": usage_status,
        "reliability_score": reliability_score,
        "quality_class": quality_class,
        "warning": warning,
    }


def can_use_model(commodity: str, market: str, farmer_facing: bool = True) -> bool:
    """
    Check if a model is approved for prediction / recommendation.

    Rules:
      - PRODUCTION_READY    : Allowed for farmer-facing & research
      - USABLE_WITH_WARNING : Allowed for farmer-facing & research
      - RESEARCH_ONLY       : Blocked if farmer_facing=True; Allowed if farmer_facing=False
      - DISABLED / MISSING  : Blocked completely
    """
    meta = get_model_quality_metadata(commodity=commodity, market=market)
    status = meta["usage_status"]

    if status == STATUS_PRODUCTION_READY:
        return True
    if status == STATUS_USABLE_WITH_WARNING:
        return True
    if status == STATUS_RESEARCH_ONLY:
        return not farmer_facing
    return False


def evaluate_model_gating(
    commodity: str,
    market: str,
    farmer_facing: bool = True
) -> ModelQualityGateResult:
    """
    Evaluate model quality gate and return full structured result.
    """
    meta = get_model_quality_metadata(commodity=commodity, market=market)
    status = meta["usage_status"]
    score = meta["reliability_score"]
    q_class = meta["quality_class"]
    warn = meta["warning"]

    allowed = can_use_model(commodity=commodity, market=market, farmer_facing=farmer_facing)

    if allowed:
        if status == STATUS_PRODUCTION_READY:
            reason = f"Model is production-ready with high reliability ({score:.1f}/100)."
        else:
            reason = f"Model is usable with warning (reliability: {score:.1f}/100)."
    else:
        if status == STATUS_RESEARCH_ONLY:
            reason = f"Model is restricted to research/dev mode only and blocked for farmer recommendations."
        elif status == STATUS_DISABLED:
            reason = f"Model is disabled due to poor baseline performance (Reliability: {score:.1f}/100)."
        else:
            reason = f"Model is missing or unregistered."

    logger.info(
        f"ModelQualityGate for {commodity}/{market} (farmer_facing={farmer_facing}): "
        f"Allowed={allowed}, Status={status}, Score={score:.1f}, Class={q_class}"
    )

    return ModelQualityGateResult(
        commodity=commodity,
        market=market,
        allowed=allowed,
        usage_status=status,
        reliability_score=score,
        quality_class=q_class,
        warning=warn,
        reason=reason
    )
