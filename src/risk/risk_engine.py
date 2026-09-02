"""
Risk Assessment & Confidence Engine.
Evaluates price volatility, spike risk, historical model error, and data recency
to output transparent risk levels, confidence scores, and warning messages across commodities.
"""
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

from src.config.commodity_registry import get_commodity_config
from src.config.config import DEFAULT_COMMODITY
from src.config.model_registry import get_registered_model
from src.utils.logger import logger


@dataclass
class RiskConfidenceOutput:
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    confidence_score: float  # Transparent score out of 100
    market_condition: str  # "NORMAL", "ELEVATED_VOLATILITY", "UNUSUAL_SPIKE"
    warning_message: str
    lower_bound_80: float = 0.0   # 80% empirical prediction interval lower bound
    upper_bound_80: float = 0.0   # 80% empirical prediction interval upper bound
    lower_bound_95: float = 0.0   # 95% empirical prediction interval lower bound
    upper_bound_95: float = 0.0   # 95% empirical prediction interval upper bound
    expected_error_margin: float = 0.0



class RiskEngine:
    """
    Evaluates market risk and computes transparent confidence scores for predictions across commodities.
    """

    def __init__(self, spike_threshold_pct: float = 10.0):
        self.spike_threshold_pct = spike_threshold_pct

    def get_market_mae(self, market: str, commodity: str = DEFAULT_COMMODITY) -> float:
        """
        Lookup recorded historical MAE for the commodity and market.
        """
        market_clean = market.strip().lower()
        comm_clean = commodity.strip().lower()

        # Check model registry first
        reg_info = get_registered_model(commodity=comm_clean, market=market_clean)
        if reg_info and "test_mae" in reg_info:
            return float(reg_info["test_mae"])

        # Check commodity config
        config = get_commodity_config(comm_clean)
        if config and market_clean in config.historical_mae:
            return float(config.historical_mae[market_clean])

        # Default conservative MAE for uncalibrated models
        return 150.0

    def evaluate_risk_and_confidence(
        self,
        market: str,
        current_price: float,
        predicted_change: float,
        recent_series: pd.Series,
        data_date: Optional[pd.Timestamp] = None,
        commodity: str = DEFAULT_COMMODITY
    ) -> RiskConfidenceOutput:
        """
        Evaluate market volatility and model error to determine risk and confidence score.

        Transparent Confidence Formula:
          Base Confidence = 100 * (1 - Relative_MAE)
          Adjusted for Volatility: - (Volatility_Std / Mean_Price) * 50
          Adjusted for Spike: - 25 if recent movement >= spike threshold
          Data Recency Penalty: - 5 per day older than 3 days
        """
        test_mae = self.get_market_mae(market=market, commodity=commodity)

        # 1. Relative historical model error penalty
        rel_error = (test_mae / current_price) if current_price > 0 else 0.20
        base_confidence = max(40.0, 100.0 * (1.0 - min(rel_error, 0.50)))

        # 2. Volatility analysis from recent observations
        if len(recent_series) >= 3:
            volatility_std = float(recent_series.tail(7).std())
            recent_pct_change = (
                abs((recent_series.iloc[-1] - recent_series.iloc[-2]) / recent_series.iloc[-2] * 100.0)
                if len(recent_series) >= 2 and recent_series.iloc[-2] > 0
                else 0.0
            )
        else:
            volatility_std = 0.0
            recent_pct_change = 0.0

        volatility_ratio = (volatility_std / current_price) if current_price > 0 else 0.0

        # 3. Spike & Risk Level Determination
        is_spike = (
            recent_pct_change >= self.spike_threshold_pct
            or (abs(predicted_change / current_price * 100) >= self.spike_threshold_pct if current_price > 0 else False)
        )

        if is_spike:
            risk_level = "HIGH"
            market_condition = "UNUSUAL_SPIKE"
            warning_message = (
                "Forecast uncertainty is elevated because recent market prices exhibit unusual volatility or sudden price spikes."
            )
            spike_penalty = 25.0
        elif volatility_ratio >= 0.08 or volatility_std >= 100.0:
            risk_level = "MEDIUM"
            market_condition = "ELEVATED_VOLATILITY"
            warning_message = (
                "Forecast uncertainty is moderate due to elevated short-term price volatility in recent market sessions."
            )
            spike_penalty = 10.0
        else:
            risk_level = "LOW"
            market_condition = "NORMAL"
            warning_message = "Market conditions are stable with normal price volatility."
            spike_penalty = 0.0

        # 4. Data Recency Penalty
        recency_penalty = 0.0
        if data_date is not None:
            days_old = (pd.Timestamp.now() - pd.to_datetime(data_date)).days
            if days_old > 3:
                recency_penalty = min(20.0, (days_old - 3) * 2.0)

        # 5. Final Transparent Confidence Score calculation
        confidence_score = base_confidence - (volatility_ratio * 40.0) - spike_penalty - recency_penalty
        confidence_score = float(np.clip(confidence_score, 15.0, 95.0))

        # 6. Statistical Prediction Intervals (Empirical Residual Scaling)
        # 80% interval ~ 1.28 * sigma_residuals (where sigma ~= 1.25 * MAE under Laplace/Normal mixture)
        # 95% interval ~ 1.96 * sigma_residuals
        sigma_res = max(10.0, test_mae * 1.25 * (1.0 + volatility_ratio))
        error_margin_80 = 1.28 * sigma_res
        error_margin_95 = 1.96 * sigma_res

        pred_price = current_price + predicted_change
        lower_80 = max(0.0, round(pred_price - error_margin_80, 2))
        upper_80 = round(pred_price + error_margin_80, 2)
        lower_95 = max(0.0, round(pred_price - error_margin_95, 2))
        upper_95 = round(pred_price + error_margin_95, 2)

        logger.info(
            f"Risk for {commodity} {market}: level={risk_level}, condition={market_condition}, "
            f"confidence_score={confidence_score:.1f}/100, "
            f"interval_80%=[Rs.{lower_80}, Rs.{upper_80}], interval_95%=[Rs.{lower_95}, Rs.{upper_95}]"
        )

        return RiskConfidenceOutput(
            risk_level=risk_level,
            confidence_score=round(confidence_score, 1),
            market_condition=market_condition,
            warning_message=warning_message,
            lower_bound_80=lower_80,
            upper_bound_80=upper_80,
            lower_bound_95=lower_95,
            upper_bound_95=upper_95,
            expected_error_margin=round(error_margin_80, 2)
        )

