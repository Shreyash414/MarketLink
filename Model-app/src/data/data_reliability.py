"""
Data Reliability & Freshness Module.
Centralized, deterministic safety layer preventing stale, insufficient, or malformed
input data from being used silently for price forecasting and mandi recommendations.

Key Distinction:
  - Data Reliability: "Can we trust the input data enough to run inference?"
  - Model Quality (Task 7): "Can we trust this model enough to show its prediction?"
Both gates must pass before a normal farmer-facing prediction is served.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from src.config.config import (
    MAX_DATA_AGE_DAYS,
    MIN_REQUIRED_HISTORY_SESSIONS,
    STALE_CACHE_ALLOWED_FOR_FARMER,
)
from src.utils.logger import logger

# Source constants
SOURCE_LIVE = "LIVE"
SOURCE_CACHE = "CACHE"

# Freshness & Status constants
STATUS_LIVE_FRESH = "LIVE_FRESH"
STATUS_CACHE_FRESH = "CACHE_FRESH"
STATUS_CACHE_STALE = "CACHE_STALE"
STATUS_INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
STATUS_INVALID_DATA = "INVALID_DATA"
STATUS_READY = "READY"
STATUS_BLOCKED = "BLOCKED"


@dataclass
class DataReliabilityResult:
    commodity: str
    market: str
    inference_allowed: bool
    status: str                 # STATUS_READY, STATUS_BLOCKED, STATUS_CACHE_STALE, etc.
    source: str                 # SOURCE_LIVE or SOURCE_CACHE
    freshness_status: str       # STATUS_LIVE_FRESH, STATUS_CACHE_FRESH, STATUS_CACHE_STALE
    observation_date: Optional[pd.Timestamp]
    age_days: int
    session_count: int
    is_fresh: bool
    is_sufficient: bool
    is_valid: bool
    reason: str
    warning: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commodity": self.commodity,
            "market": self.market,
            "inference_allowed": self.inference_allowed,
            "status": self.status,
            "source": self.source,
            "freshness_status": self.freshness_status,
            "observation_date": str(self.observation_date.date()) if self.observation_date and hasattr(self.observation_date, "date") else None,
            "age_days": self.age_days,
            "session_count": self.session_count,
            "is_fresh": self.is_fresh,
            "is_sufficient": self.is_sufficient,
            "is_valid": self.is_valid,
            "reason": self.reason,
            "warning": self.warning,
        }


def evaluate_data_freshness(
    observation_date: Optional[pd.Timestamp],
    source: str = SOURCE_CACHE,
    current_date: Optional[pd.Timestamp] = None,
    max_age_days: int = MAX_DATA_AGE_DAYS,
) -> Tuple[str, int, bool]:
    """
    Evaluate observation date freshness against system date and source semantics.

    Rules:
      - source == "LIVE": freshness_status = LIVE_FRESH, is_fresh = True
      - source == "CACHE":
          - age <= max_age_days -> CACHE_FRESH, is_fresh = True
          - age > max_age_days  -> CACHE_STALE, is_fresh = False
      - CACHE source is NEVER labeled LIVE.
    """
    if observation_date is None or pd.isna(observation_date):
        return STATUS_CACHE_STALE, 9999, False

    try:
        obs_dt = pd.to_datetime(observation_date)
    except Exception:
        return STATUS_CACHE_STALE, 9999, False

    ref_date = pd.to_datetime(current_date) if current_date is not None else pd.Timestamp(datetime.now().date())
    
    # Calculate age in days
    age_days = (ref_date.normalize() - obs_dt.normalize()).days
    if age_days < 0:
        age_days = 0

    norm_source = str(source).strip().upper()
    if norm_source == SOURCE_LIVE:
        return STATUS_LIVE_FRESH, age_days, True
    
    # Cache source evaluation
    if age_days <= max_age_days:
        return STATUS_CACHE_FRESH, age_days, True
    else:
        return STATUS_CACHE_STALE, age_days, False


def validate_price_data(
    df: pd.DataFrame,
    commodity: Optional[str] = None,
    market: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Validate current or merged dataframe for numeric integrity and range checks.

    Checks:
      - Non-empty dataframe
      - Required columns (date, modal_price)
      - No NaN or Infinity in modal_price
      - modal_price > 0
      - min_price >= 0 and max_price >= 0 (if present)
      - min_price <= modal_price <= max_price (if present)
      - Valid non-null datetime objects
      - No duplicate (market, date) timestamps
    """
    if df is None or df.empty:
        return False, "Dataframe is empty or null."

    cols = [col.strip().lower() for col in df.columns]
    if "date" not in cols or "modal_price" not in cols:
        return False, "Data missing required 'date' or 'modal_price' columns."

    df_check = df.copy()
    df_check.columns = [col.strip().lower() for col in df_check.columns]

    # Validate dates
    try:
        dates = pd.to_datetime(df_check["date"], errors="coerce")
        if dates.isna().any():
            return False, "Date column contains NaT or unparseable datetime strings."
    except Exception as e:
        return False, f"Error parsing dates: {e}"

    # Duplicate check by market and date
    if "market" in df_check.columns:
        dups = df_check.duplicated(subset=["market", "date"])
        if dups.any():
            return False, f"Duplicate timestamps ({dups.sum()} rows) detected for market observation."

    # Validate modal price
    prices = pd.to_numeric(df_check["modal_price"], errors="coerce")
    if prices.isna().any():
        return False, "modal_price column contains NaN or non-numeric values."

    if np.isinf(prices).any():
        return False, "modal_price column contains Infinity values."

    if (prices <= 0).any():
        return False, "modal_price contains non-positive values (<= 0)."

    # Validate min_price and max_price if present
    if "min_price" in df_check.columns:
        min_prices = pd.to_numeric(df_check["min_price"].dropna(), errors="coerce")
        if np.isinf(min_prices).any() or (min_prices < 0).any():
            return False, "min_price contains invalid negative or infinite values."

    if "max_price" in df_check.columns:
        max_prices = pd.to_numeric(df_check["max_price"].dropna(), errors="coerce")
        if np.isinf(max_prices).any() or (max_prices < 0).any():
            return False, "max_price contains invalid negative or infinite values."

    if "min_price" in df_check.columns and "max_price" in df_check.columns:
        valid_range_rows = df_check.dropna(subset=["min_price", "modal_price", "max_price"])
        if not valid_range_rows.empty:
            latest_row = valid_range_rows.iloc[-1]
            min_p = float(latest_row["min_price"])
            mod_p = float(latest_row["modal_price"])
            max_p = float(latest_row["max_price"])
            if min_p > 0 and max_p > 0:
                if min_p > mod_p or mod_p > max_p:
                    return False, f"Price range logic failure: min_price ({min_p}) > modal_price ({mod_p}) or modal_price > max_price ({max_p})."

    return True, "Data validation passed."



def evaluate_historical_sufficiency(
    df: pd.DataFrame,
    min_sessions: int = MIN_REQUIRED_HISTORY_SESSIONS,
) -> Tuple[bool, int, str]:
    """
    Verify that enough usable, chronologically ordered sessions exist for lag/rolling features.

    Checks:
      - Valid non-null price observations count >= min_sessions
      - Chronological ordering
    """
    if df is None or df.empty:
        return False, 0, "No historical data available."

    valid_df = df.dropna(subset=["modal_price", "date"])
    session_count = len(valid_df)

    if session_count < min_sessions:
        return (
            False,
            session_count,
            f"Insufficient historical warm-up sessions ({session_count} available, {min_sessions} required for 30-day V3 features).",
        )

    # Check chronological ordering
    dates = pd.to_datetime(valid_df["date"])
    if not dates.is_monotonic_increasing:
        sorted_dates = dates.sort_values()
        if len(sorted_dates) < min_sessions:
            return False, session_count, "Historical sessions are not strictly ordered or contain unparseable dates."

    return True, session_count, f"Sufficient history available ({session_count} sessions)."


def evaluate_data_reliability(
    commodity: str,
    market: str,
    merged_df: pd.DataFrame,
    source: str = SOURCE_CACHE,
    current_date: Optional[pd.Timestamp] = None,
    farmer_facing: bool = True,
    max_age_days: int = MAX_DATA_AGE_DAYS,
    min_sessions: int = MIN_REQUIRED_HISTORY_SESSIONS,
    stale_allowed_farmer: bool = STALE_CACHE_ALLOWED_FOR_FARMER,
) -> DataReliabilityResult:
    """
    Centralized data reliability evaluation function.
    Combines price validation, historical warm-up sufficiency, and freshness status.
    """
    comm_clean = commodity.strip()
    market_clean = market.strip()
    norm_source = str(source).strip().upper()
    if norm_source not in (SOURCE_LIVE, SOURCE_CACHE):
        norm_source = SOURCE_CACHE

    # 1. Price Data Validation
    is_valid, val_reason = validate_price_data(merged_df, commodity=comm_clean, market=market_clean)
    if not is_valid:
        logger.warning(f"DataReliability for {comm_clean}/{market_clean}: INVALID_DATA ({val_reason})")
        return DataReliabilityResult(
            commodity=comm_clean,
            market=market_clean,
            inference_allowed=False,
            status=STATUS_INVALID_DATA,
            source=norm_source,
            freshness_status=STATUS_CACHE_STALE if norm_source == SOURCE_CACHE else STATUS_LIVE_FRESH,
            observation_date=None,
            age_days=9999,
            session_count=len(merged_df) if merged_df is not None else 0,
            is_fresh=False,
            is_sufficient=False,
            is_valid=False,
            reason=val_reason,
            warning=f"Data validation failed for {comm_clean} {market_clean}: {val_reason}",
        )

    # Latest observation date and session count
    df_sorted = merged_df.sort_values("date").reset_index(drop=True)
    latest_obs_date = pd.to_datetime(df_sorted["date"].iloc[-1])

    # 2. Freshness Evaluation
    freshness_status, age_days, is_fresh = evaluate_data_freshness(
        observation_date=latest_obs_date,
        source=norm_source,
        current_date=current_date,
        max_age_days=max_age_days,
    )

    # 3. Historical Sufficiency
    is_sufficient, session_count, suff_reason = evaluate_historical_sufficiency(
        df_sorted, min_sessions=min_sessions
    )

    if not is_sufficient:
        logger.warning(f"DataReliability for {comm_clean}/{market_clean}: INSUFFICIENT_HISTORY ({suff_reason})")
        return DataReliabilityResult(
            commodity=comm_clean,
            market=market_clean,
            inference_allowed=False,
            status=STATUS_INSUFFICIENT_HISTORY,
            source=norm_source,
            freshness_status=freshness_status,
            observation_date=latest_obs_date,
            age_days=age_days,
            session_count=session_count,
            is_fresh=is_fresh,
            is_sufficient=False,
            is_valid=True,
            reason=suff_reason,
            warning=f"Insufficient historical data ({session_count}/{min_sessions} sessions) for {comm_clean} {market_clean}.",
        )

    # 4. Final Inference Decision based on Freshness & Policy
    warning_msg = ""
    inference_allowed = True
    status = STATUS_READY

    if freshness_status == STATUS_CACHE_STALE:
        status = STATUS_CACHE_STALE
        warning_msg = (
            f"Market data for {comm_clean} {market_clean} is from cached data ({age_days} days old, "
            f"threshold: {max_age_days} days)."
        )
        if farmer_facing and not stale_allowed_farmer:
            inference_allowed = False
            status = STATUS_BLOCKED
            reason = f"Cache data is stale ({age_days} days old) and blocked for farmer-facing recommendations."
        else:
            reason = f"Cache data is stale ({age_days} days old) but allowed under current policy."
    elif freshness_status == STATUS_CACHE_FRESH:
        warning_msg = f"Market data fetched from recent cache ({age_days} days old)."
        reason = f"Recent cache data is valid and fresh ({age_days} days old)."
    else:
        reason = f"Live API market data is fresh ({age_days} days old)."

    logger.info(
        f"DataReliability for {comm_clean}/{market_clean}: "
        f"Allowed={inference_allowed}, Status={status}, Source={norm_source}, Freshness={freshness_status}, "
        f"Age={age_days}d, Sessions={session_count}"
    )

    return DataReliabilityResult(
        commodity=comm_clean,
        market=market_clean,
        inference_allowed=inference_allowed,
        status=status,
        source=norm_source,
        freshness_status=freshness_status,
        observation_date=latest_obs_date,
        age_days=age_days,
        session_count=session_count,
        is_fresh=is_fresh,
        is_sufficient=True,
        is_valid=True,
        reason=reason,
        warning=warning_msg,
    )
