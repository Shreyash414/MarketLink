"""
Inference Feature Generator Module.
Generates exact V3 features for live/current market forecasting matching
the validated ML pipeline training methodology.
"""
from typing import List, Tuple
import numpy as np
import pandas as pd

from src.utils.logger import logger


def generate_v3_features(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate all base and V3 features for a chronologically sorted time-series.

    Parameters
    ----------
    df : pd.DataFrame
        Chronologically sorted market time series containing 'date' and 'modal_price'.

    Returns
    -------
    pd.DataFrame
        DataFrame with full set of features.
    """
    if df.empty or len(df) < 31:
        logger.warning(
            f"Dataframe length ({len(df)}) is too short to compute 30-day lag/rolling features."
        )
        return pd.DataFrame()

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Price
    price = pd.to_numeric(df["modal_price"], errors="coerce")

    # ========================================================
    # TIME FEATURES
    # ========================================================
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_year"] = df["date"].dt.dayofyear

    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["day_of_year_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365.25)
    df["day_of_year_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365.25)

    # ========================================================
    # LAG FEATURES
    # ========================================================
    df["lag_1"] = price.shift(1)
    df["lag_2"] = price.shift(2)
    df["lag_3"] = price.shift(3)
    df["lag_7"] = price.shift(7)
    df["lag_14"] = price.shift(14)
    df["lag_30"] = price.shift(30)

    # ========================================================
    # ROLLING STATISTICS
    # ========================================================
    prev_price = price.shift(1)
    df["rolling_mean_3"] = prev_price.rolling(3).mean()
    df["rolling_mean_7"] = prev_price.rolling(7).mean()
    df["rolling_mean_14"] = prev_price.rolling(14).mean()
    df["rolling_mean_30"] = prev_price.rolling(30).mean()

    df["rolling_std_7"] = prev_price.rolling(7).std()
    df["rolling_std_14"] = prev_price.rolling(14).std()
    df["rolling_std_30"] = prev_price.rolling(30).std()

    # ========================================================
    # MOMENTUM FEATURES (Base)
    # ========================================================
    df["price_change_1"] = price.shift(1) - price.shift(2)
    df["price_change_7"] = price.shift(1) - price.shift(8)

    prev_1 = price.shift(2)
    prev_7 = price.shift(8)
    df["price_change_pct_1"] = ((price.shift(1) - prev_1) / prev_1.replace(0, np.nan)) * 100
    df["price_change_pct_7"] = ((price.shift(1) - prev_7) / prev_7.replace(0, np.nan)) * 100

    # ========================================================
    # V3 FEATURES
    # ========================================================
    df["price_change_abs_1"] = df["price_change_1"].abs()
    df["price_change_abs_7"] = df["price_change_7"].abs()

    df["momentum_3"] = price - price.shift(3)
    df["momentum_7"] = price - price.shift(7)
    df["momentum_14"] = price - price.shift(14)
    df["momentum_30"] = price - price.shift(30)

    df["momentum_pct_3"] = (df["momentum_3"] / price.shift(3).replace(0, np.nan)) * 100
    df["momentum_pct_7"] = (df["momentum_7"] / price.shift(7).replace(0, np.nan)) * 100
    df["momentum_pct_14"] = (df["momentum_14"] / price.shift(14).replace(0, np.nan)) * 100

    df["price_volatility_3"] = prev_price.rolling(3).std()
    df["price_volatility_7"] = prev_price.rolling(7).std()
    df["price_volatility_14"] = prev_price.rolling(14).std()
    df["price_volatility_30"] = prev_price.rolling(30).std()

    df["recent_max_7"] = prev_price.rolling(7).max()
    df["recent_min_7"] = prev_price.rolling(7).min()
    df["recent_max_14"] = prev_price.rolling(14).max()
    df["recent_min_14"] = prev_price.rolling(14).min()
    df["recent_max_30"] = prev_price.rolling(30).max()
    df["recent_min_30"] = prev_price.rolling(30).min()

    df["distance_from_high_7"] = price - df["recent_max_7"]
    df["distance_from_low_7"] = price - df["recent_min_7"]
    df["distance_from_high_14"] = price - df["recent_max_14"]
    df["distance_from_low_14"] = price - df["recent_min_14"]

    df["price_range_7"] = df["recent_max_7"] - df["recent_min_7"]
    df["price_range_14"] = df["recent_max_14"] - df["recent_min_14"]
    df["price_range_30"] = df["recent_max_30"] - df["recent_min_30"]

    df["price_range_pct_7"] = (df["price_range_7"] / price.replace(0, np.nan)) * 100
    df["price_range_pct_14"] = (df["price_range_14"] / price.replace(0, np.nan)) * 100
    df["price_range_pct_30"] = (df["price_range_30"] / price.replace(0, np.nan)) * 100

    df["volatility_ratio_7_30"] = df["price_volatility_7"] / df["price_volatility_30"].replace(0, np.nan)

    df["trend_strength_7"] = df["momentum_7"] / df["price_volatility_7"].replace(0, np.nan)
    df["trend_strength_14"] = df["momentum_14"] / df["price_volatility_14"].replace(0, np.nan)

    range_7 = df["recent_max_7"] - df["recent_min_7"]
    range_14 = df["recent_max_14"] - df["recent_min_14"]
    df["price_position_7"] = (price - df["recent_min_7"]) / range_7.replace(0, np.nan)
    df["price_position_14"] = (price - df["recent_min_14"]) / range_14.replace(0, np.nan)

    # Categorical code fallbacks if present in model feature lists
    for code_col in ["commodity_code", "market_code", "state_code", "variety_code", "grade_code"]:
        if code_col not in df.columns:
            df[code_col] = 0.0

    # Clean infinite/NaN
    df = df.replace([np.inf, -np.inf], np.nan).infer_objects(copy=False)

    return df




def get_latest_inference_features(
    merged_df: pd.DataFrame,
    required_features: List[str]
) -> Tuple[pd.DataFrame, float, pd.Timestamp]:
    """
    Extract feature vector for the latest available observation session.

    Returns
    -------
    Tuple[pd.DataFrame, float, pd.Timestamp]
        (X_inference DataFrame with required_features columns, current_price, latest_date)
    """
    full_featured = generate_v3_features(merged_df)
    if full_featured.empty:
        raise ValueError("Failed to generate V3 features due to insufficient historical observations.")

    latest_row = full_featured.tail(1).copy()
    latest_date = pd.to_datetime(latest_row["date"].values[0])
    current_price = float(latest_row["modal_price"].values[0])

    # Ensure all required feature columns exist
    missing_feats = [f for f in required_features if f not in latest_row.columns]
    if missing_feats:
        raise KeyError(
            f"The following required features were missing from the generated V3 features: {missing_feats}"
        )

    X_inference = latest_row[required_features].copy()
    return X_inference, current_price, latest_date
