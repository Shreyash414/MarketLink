"""
Historical Merger Module.
Combines recent historical mandi data with fresh current mandi data
to ensure sufficient lookback window for lag and rolling feature calculations.
"""
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from src.config.config import PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.utils.logger import logger


def load_historical_mandi_data(
    market: str,
    commodity: str = "Onion"
) -> pd.DataFrame:
    """
    Load cleaned historical data for a specific market.
    """
    market_clean = market.strip().lower()
    processed_path = PROCESSED_DATA_DIR / f"{commodity.lower()}_{market_clean}_model.csv"
    raw_path = RAW_DATA_DIR / f"{commodity.lower()}_{market_clean}_history.csv"

    if processed_path.exists():
        df = pd.read_csv(processed_path)
    elif raw_path.exists():
        df = pd.read_csv(raw_path)
    else:
        logger.warning(f"No historical file found for market: {market} at {processed_path}")
        return pd.DataFrame()

    df.columns = [col.strip().lower() for col in df.columns]
    
    # Normalize date
    date_col = next((c for c in ["date", "arrival_date", "reported_date"] if c in df.columns), None)
    if date_col:
        df["date"] = pd.to_datetime(df[date_col], errors="coerce")
    
    # Normalize price
    if "modal_price" not in df.columns and "modal_price" in df.columns:
        df["modal_price"] = pd.to_numeric(df["modal_price"], errors="coerce")

    # Keep relevant columns
    cols = [c for c in ["date", "market", "commodity", "state", "district", "modal_price", "min_price", "max_price"] if c in df.columns]
    df = df[cols].dropna(subset=["date", "modal_price"]).copy()
    df["market"] = market.strip()
    return df


def merge_current_with_history(
    current_df: pd.DataFrame,
    market: str,
    commodity: str = "Onion",
    min_history_sessions: int = 45
) -> pd.DataFrame:
    """
    Combine recent history with current observation for a market.
    Sorted chronologically and deduplicated by date.
    """
    history_df = load_historical_mandi_data(market=market, commodity=commodity)
    
    market_current = current_df[
        current_df["market"].astype(str).str.lower() == market.strip().lower()
    ].copy() if not current_df.empty else pd.DataFrame()

    if history_df.empty and market_current.empty:
        logger.error(f"No data available for market {market}")
        return pd.DataFrame()

    # Combine datasets
    combined = pd.concat([history_df, market_current], ignore_index=True)
    
    # Convert date and numeric fields
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
    combined["modal_price"] = pd.to_numeric(combined["modal_price"], errors="coerce")
    
    # Drop NaNs
    combined = combined.dropna(subset=["date", "modal_price"]).copy()
    
    # Deduplicate by date, keeping latest
    combined = combined.sort_values("date").drop_duplicates(
        subset=["date"], keep="last"
    ).reset_index(drop=True)

    logger.info(
        f"Merged dataset for {market}: total observed sessions = {len(combined)}, "
        f"date range: {combined['date'].min().date()} to {combined['date'].max().date()}"
    )

    return combined
