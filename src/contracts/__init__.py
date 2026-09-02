"""
Contracts package initialization.
"""
from src.contracts.inference_contract import (
    CONTRACT_VERSION,
    CanonicalInferenceItem,
    CanonicalRecommendationResponse,
    ContractMetadata,
    build_canonical_recommendation,
    validate_inference_contract,
)

__all__ = [
    "CONTRACT_VERSION",
    "ContractMetadata",
    "CanonicalInferenceItem",
    "CanonicalRecommendationResponse",
    "validate_inference_contract",
    "build_canonical_recommendation",
]
