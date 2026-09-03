"""
Model Predictor Module.
Loads existing pre-trained XGBoost V3 models and selected feature configurations,
executing fresh price forecasting separate from training.
Supports multi-commodity model resolution and dynamic model loading.
"""
from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb

from src.config.commodity_registry import get_commodity_config
from src.config.config import DEFAULT_COMMODITY, MODEL_DIR, get_model_dir
from src.config.model_registry import get_registered_model, load_model_registry
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

    # Process-wide thread-safe model and feature cache
    # Cache key: (commodity_clean, market_clean, optional_custom_dir_str)
    _shared_models: Dict[Tuple[str, str, Optional[str]], xgb.XGBRegressor] = {}
    _shared_features: Dict[Tuple[str, str, Optional[str]], List[str]] = {}
    _cache_lock = threading.Lock()

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

    @classmethod
    def is_model_cached(
        cls,
        market: str,
        commodity: Optional[str] = None,
        custom_model_dir: Optional[Path] = None
    ) -> bool:
        """
        Check if a specific model is currently cached in process memory.
        """
        comm_clean = (commodity or DEFAULT_COMMODITY).strip().lower()
        market_clean = market.strip().lower()
        dir_key = str(Path(custom_model_dir).resolve()) if custom_model_dir else None
        with cls._cache_lock:
            return (comm_clean, market_clean, dir_key) in cls._shared_models

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear all process-wide cached models and feature sets.
        """
        with cls._cache_lock:
            cls._shared_models.clear()
            cls._shared_features.clear()

    @classmethod
    def get_loaded_models_count(cls) -> int:
        """
        Return the number of models currently cached in-memory across the process.
        """
        with cls._cache_lock:
            return len(cls._shared_models)

    def preload_models(self, commodity: Optional[str] = None) -> Dict[str, bool]:
        """
        Preload models for a specific commodity or all registered commodities into the shared cache.
        Returns a mapping of (commodity:market) -> load_success.
        """
        registry = load_model_registry()
        results: Dict[str, bool] = {}
        for comm_name, markets in registry.items():
            if commodity and comm_name.lower() != commodity.strip().lower():
                continue
            for mkt_name in markets.keys():
                key = f"{comm_name}:{mkt_name}"
                try:
                    self.load_market_model(market=mkt_name, commodity=comm_name)
                    results[key] = True
                except Exception as e:
                    logger.warning(f"Could not preload model for {key}: {e}")
                    results[key] = False
        return results

    def load_market_model(
        self,
        market: str,
        commodity: Optional[str] = None
    ) -> Tuple[xgb.XGBRegressor, List[str]]:
        """
        Load pre-trained model and required feature list for a market and commodity.
        Utilizes thread-safe process-level cache so expensive model files are loaded
        from disk only once and reused across subsequent requests and worker calls.
        """
        comm = commodity or self.default_commodity
        comm_clean = comm.strip().lower()
        market_clean = market.strip().lower()
        cache_key = (comm_clean, market_clean)
        dir_key = str(self.custom_model_dir.resolve()) if self.custom_model_dir else None
        shared_cache_key = (comm_clean, market_clean, dir_key)

        # 1. Fast check in instance-level cache
        if cache_key in self._loaded_models:
            return self._loaded_models[cache_key], self._loaded_features[cache_key]

        # 2. Check process-level shared cache with thread safety
        with self._cache_lock:
            if shared_cache_key in self._shared_models:
                model = self._shared_models[shared_cache_key]
                feature_list = self._shared_features[shared_cache_key]
                self._loaded_models[cache_key] = model
                self._loaded_features[cache_key] = feature_list
                return model, feature_list

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

            # 3. Explicit runtime artifact validation with descriptive error messages
            if not model_file.exists():
                raise FileNotFoundError(
                    f"Required model artifact not found for commodity '{comm}', market '{market}'. "
                    f"Expected path: {model_file.resolve()}. "
                    f"Please verify model artifact deployment."
                )
            if not feature_file.exists():
                raise FileNotFoundError(
                    f"Required feature CSV artifact not found for commodity '{comm}', market '{market}'. "
                    f"Expected path: {feature_file.resolve()}. "
                    f"Please ensure feature CSV artifacts are included in deployment."
                )

            # Load feature list from required feature CSV artifact
            features_df = pd.read_csv(feature_file)
            if "feature" not in features_df.columns:
                raise ValueError(
                    f"Invalid feature CSV artifact for '{comm}/{market}': column 'feature' not found in {feature_file.resolve()}"
                )
            feature_list = features_df["feature"].tolist()

            # Load XGBoost model
            model = xgb.XGBRegressor()
            model.load_model(model_file)

            logger.info(
                f"Successfully loaded model for {comm} market '{market}' with {len(feature_list)} features from {model_file}"
            )

            # Populate both shared process-level cache and instance-level cache
            self._shared_models[shared_cache_key] = model
            self._shared_features[shared_cache_key] = feature_list
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


_shared_predictor_instance: Optional[ModelPredictor] = None
_shared_predictor_lock = threading.Lock()


def get_shared_predictor() -> ModelPredictor:
    """
    Return a shared ModelPredictor instance using the thread-safe model cache.
    Ensures model lifecycle reuse across recommendation requests and future AI worker calls.
    """
    global _shared_predictor_instance
    if _shared_predictor_instance is None:
        with _shared_predictor_lock:
            if _shared_predictor_instance is None:
                _shared_predictor_instance = ModelPredictor()
    return _shared_predictor_instance


