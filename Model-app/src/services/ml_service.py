"""
ML Service Layer.
Thin, thread-safe service coordinating prediction and recommendation requests
with the underlying pre-trained models using the shared model provider.
"""
from typing import Any, Dict, Optional
import pandas as pd

from src.contracts.inference_contract import CanonicalRecommendationResponse
from src.core.exceptions import (
    ArtifactNotFoundException,
    InvalidInputException,
    ModelServiceException,
    ModelUnavailableException,
)
from src.models.model_predictor import get_shared_predictor
from src.recommendation.mandi_recommender import recommend_canonical
from src.utils.logger import logger


class MLService:
    """Service providing high-level interface to ML recommendation and inference."""

    def __init__(self):
        self.shared_predictor = get_shared_predictor()

    def get_recommendation(
        self,
        farmer_latitude: float,
        farmer_longitude: float,
        quantity_quintals: float,
        commodity: str = "Onion",
        max_distance_km: Optional[float] = None,
        transport_rate: float = 3.0,
        farmer_facing: bool = True,
    ) -> CanonicalRecommendationResponse:
        """
        Execute full recommendation pipeline given farmer location and produce quantity.
        Uses request-isolated MandiRecommender with shared in-memory model instances.
        """
        try:
            canonical = recommend_canonical(
                farmer_latitude=farmer_latitude,
                farmer_longitude=farmer_longitude,
                quantity_quintals=quantity_quintals,
                commodity=commodity,
                max_distance_km=max_distance_km,
                transport_rate=transport_rate,
                farmer_facing=farmer_facing,
            )
            return canonical
        except ValueError as e:
            raise InvalidInputException(str(e))
        except FileNotFoundError as e:
            raise ArtifactNotFoundException(str(e))
        except PermissionError as e:
            raise ModelUnavailableException(str(e))
        except Exception as e:
            logger.error(f"Unexpected error during ML recommendation: {e}")
            raise ModelServiceException(f"Failed to execute recommendation: {e}")

    def predict_single(
        self,
        market: str,
        commodity: str,
        current_price: float,
        features: Dict[str, float],
        date: Optional[str] = None,
        farmer_facing: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute direct single-mandi model prediction using the shared model provider.
        """
        try:
            # Construct single-row DataFrame from provided features
            X_df = pd.DataFrame([features])
            ts = pd.Timestamp(date) if date else pd.Timestamp.now()

            pred_out = self.shared_predictor.predict_next_price(
                market=market,
                X_features=X_df,
                current_price=current_price,
                latest_date=ts,
                commodity=commodity,
                farmer_facing=farmer_facing,
            )
            return {
                "market": pred_out.market,
                "commodity": pred_out.commodity,
                "current_price": pred_out.current_price,
                "predicted_price": pred_out.predicted_price,
                "expected_change": pred_out.expected_change,
                "expected_change_pct": pred_out.expected_change_pct,
                "expected_direction": pred_out.expected_direction,
                "usage_status": pred_out.usage_status,
                "reliability_score": pred_out.reliability_score,
                "quality_class": pred_out.quality_class,
                "data_source": "DIRECT",
            }
        except FileNotFoundError as e:
            raise ArtifactNotFoundException(str(e))
        except PermissionError as e:
            raise ModelUnavailableException(str(e))
        except KeyError as e:
            raise InvalidInputException(f"Missing required feature: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during single prediction: {e}")
            raise ModelServiceException(f"Failed to execute prediction: {e}")


# Shared singleton service instance
ml_service = MLService()
