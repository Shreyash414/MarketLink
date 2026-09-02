"""
Model Predictor Module.
Loads existing pre-trained XGBoost V3 models and selected feature configurations,
executing fresh price forecasting separate from training.
Supports multi-commodity model resolution and dynamic model loading.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb

from src.config.commodity_registry import get_commodity_config
from src.config.config import DEFAULT_COMMODITY, MODEL_DIR, get_model_dir
from src.config.model_registry import get_registered_model
from src.utils.logger import logger


from src.models.model_quality_gate import can_use_model, evaluate_model_gating


@dataclass
class PredictionOutput:
    market: str
    date: pd.Timestamp
    current_price: float
    predicted_price: float
    expected_change: float
    expected_change_pct: float
    expected_direction: str
    commodity: str = DEFAULT_COMMODITY
    usage_status: str = "PRODUCTION_READY"
    reliability_score: float = 0.0
    quality_class: str = "STRONG"
    data_source: str = "CACHE"
    data_freshness_status: str = "CACHE_FRESH"
    data_age_days: int = 0
    historical_session_count: int = 0
    data_reliability_status: str = "READY"


class ModelPredictor:
    """
    Inference manager for pre-trained XGBoost V3 price forecasting models.
    Supports multi-commodity model discovery, registry lookup, caching, quality gating, and data reliability.
    """

    def __init__(
        self,
        default_commodity: str = DEFAULT_COMMODITY,
        model_dir: Optional[Path] = None
    ):
        self.default_commodity = default_commodity
        self.custom_model_dir = Path(model_dir) if model_dir else None
        self._loaded_models: Dict[Tuple[str, str], xgb.XGBRegressor] = {}
        self._loaded_features: Dict[Tuple[str, str], List[str]] = {}

    def get_model_dir_for_commodity(self, commodity: str) -> Path:
        """
        Resolve directory containing model files for a commodity.
        """
        if self.custom_model_dir is not None:
            return self.custom_model_dir
        return get_model_dir(commodity=commodity)

    def load_market_model(
        self,
        market: str,
        commodity: Optional[str] = None
    ) -> Tuple[xgb.XGBRegressor, List[str]]:
        """
        Load pre-trained model and required feature list for a market and commodity.
        """
        comm = commodity or self.default_commodity
        comm_clean = comm.strip().lower()
        market_clean = market.strip().lower()
        cache_key = (comm_clean, market_clean)

        if cache_key in self._loaded_models:
            return self._loaded_models[cache_key], self._loaded_features[cache_key]

        target_dir = self.get_model_dir_for_commodity(comm)

        # Check registered model metadata if available
        reg_info = get_registered_model(commodity=comm, market=market)
        if reg_info and "model_file" in reg_info and "feature_file" in reg_info:
            model_file = target_dir / reg_info["model_file"]
            feature_file = target_dir / reg_info["feature_file"]
        else:
            model_file = target_dir / f"{market_clean}_final_model.json"
            feature_file = target_dir / f"{market_clean}_final_features.csv"

        # Fallback to default MODEL_DIR if commodity is Onion or not found in target_dir
        if not model_file.exists() and MODEL_DIR.exists():
            fallback_model = MODEL_DIR / f"{market_clean}_final_model.json"
            fallback_feature = MODEL_DIR / f"{market_clean}_final_features.csv"
            if fallback_model.exists() and fallback_feature.exists():
                model_file = fallback_model
                feature_file = fallback_feature

        if not model_file.exists():
            raise FileNotFoundError(
                f"Trained model file not found for commodity '{comm}' market '{market}': {model_file}"
            )
        if not feature_file.exists():
            raise FileNotFoundError(
                f"Selected feature list file not found for commodity '{comm}' market '{market}': {feature_file}"
            )

        # Load feature list
        features_df = pd.read_csv(feature_file)
        feature_list = features_df["feature"].tolist()

        # Load XGBoost model
        model = xgb.XGBRegressor()
        model.load_model(model_file)

        logger.info(
            f"Successfully loaded model for {comm} market '{market}' with {len(feature_list)} features from {model_file}"
        )

        self._loaded_models[cache_key] = model
        self._loaded_features[cache_key] = feature_list
        return model, feature_list

    def predict_next_price(
        self,
        market: str,
        X_features: pd.DataFrame,
        current_price: float,
        latest_date: pd.Timestamp,
        commodity: Optional[str] = None,
        farmer_facing: bool = True,
        data_reliability: Optional[Any] = None,
    ) -> PredictionOutput:
        """
        Predict next observed session price change and reconstruct target price.
        Enforces ModelQualityGate and DataReliability gate.
        """
        comm = commodity or self.default_commodity

        # Enforce Data Reliability Gate if provided
        if data_reliability is not None and hasattr(data_reliability, "inference_allowed"):
            if not data_reliability.inference_allowed:
                raise PermissionError(
                    f"Data reliability check blocked inference for commodity '{comm}' market '{market}'. "
                    f"Reason: {data_reliability.reason}"
                )

        # Enforce Model Quality Gate
        gate = evaluate_model_gating(commodity=comm, market=market, farmer_facing=farmer_facing)
        if not gate.allowed:
            raise PermissionError(
                f"Model for commodity '{comm}' market '{market}' is not approved for farmer-facing inference. "
                f"Reason: {gate.reason}"
            )

        model, required_features = self.load_market_model(market=market, commodity=comm)

        # Ensure correct column ordering
        X_input = X_features[required_features].copy()

        predicted_change_array = model.predict(X_input)
        predicted_change = float(predicted_change_array[0])

        predicted_price = float(current_price + predicted_change)
        expected_change_pct = float((predicted_change / current_price) * 100.0) if current_price > 0 else 0.0

        if expected_change_pct > 1.0:
            direction = "UP"
        elif expected_change_pct < -1.0:
            direction = "DOWN"
        else:
            direction = "STABLE"

        output = PredictionOutput(
            market=market.strip(),
            date=latest_date,
            current_price=round(current_price, 2),
            predicted_price=round(predicted_price, 2),
            expected_change=round(predicted_change, 2),
            expected_change_pct=round(expected_change_pct, 2),
            expected_direction=direction,
            commodity=comm,
            usage_status=gate.usage_status,
            reliability_score=gate.reliability_score,
            quality_class=gate.quality_class,
            data_source=data_reliability.source if data_reliability else "CACHE",
            data_freshness_status=data_reliability.freshness_status if data_reliability else "CACHE_FRESH",
            data_age_days=data_reliability.age_days if data_reliability else 0,
            historical_session_count=data_reliability.session_count if data_reliability else 0,
            data_reliability_status=data_reliability.status if data_reliability else "READY",
        )

        logger.info(
            f"Prediction for {comm} {market} (Status={gate.usage_status}): Current=Rs.{output.current_price}, "
            f"Predicted=Rs.{output.predicted_price} ({output.expected_change_pct:+.2f}%, {output.expected_direction})"
        )

        return output


