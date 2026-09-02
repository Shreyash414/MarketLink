"""
Commodity Data Discovery & Market Quality Scoring Tool.
Automatically discovers active mandis for any given commodity,
evaluates historical and current data quality, and ranks candidate markets for ML training.
"""
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config.commodity_registry import get_commodity_config
from src.config.config import PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.data.ingestion.current_data_fetcher import CurrentDataFetcher
from src.utils.logger import logger


def score_market_quality(
    df_market: pd.DataFrame,
    market_name: str,
    commodity: str
) -> Dict[str, any]:
    """
    Calculate data quality score (0-100) for a mandi time-series.
    """
    if df_market.empty:
        return {
            "market": market_name,
            "commodity": commodity,
            "total_records": 0,
            "quality_score": 0.0,
            "status": "INSUFFICIENT_DATA"
        }

    df = df_market.copy()
    date_col = next((c for c in ["date", "arrival_date", "reported_date"] if c in df.columns), None)
    if date_col:
        df["date"] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    total_records = len(df)
    unique_dates = df["date"].nunique() if "date" in df.columns else total_records

    # Price stats
    price_col = next((c for c in ["modal_price", "modal_price"] if c in df.columns), None)
    if price_col:
        prices = pd.to_numeric(df[price_col], errors="coerce").dropna()
        valid_prices = (prices > 0).sum()
        price_validity_ratio = valid_prices / max(1, total_records)
        mean_price = float(prices.mean()) if len(prices) > 0 else 0.0
        std_price = float(prices.std()) if len(prices) > 1 else 0.0
        cv_price = (std_price / mean_price) if mean_price > 0 else 1.0
    else:
        price_validity_ratio = 0.5
        cv_price = 0.5

    # Date range and span
    if "date" in df.columns and len(df) > 1:
        start_date = df["date"].min()
        end_date = df["date"].max()
        days_span = max(1, (end_date - start_date).days)
        density = unique_dates / days_span
    else:
        start_date = "N/A"
        end_date = "N/A"
        days_span = 0
        density = 0.1

    # Score components:
    # 1. Volume score (up to 40 pts): 1000+ sessions = 40 pts
    volume_score = min(40.0, (unique_dates / 1000.0) * 40.0)

    # 2. Price validity score (up to 30 pts)
    validity_score = price_validity_ratio * 30.0

    # 3. Density/Continuity score (up to 20 pts)
    density_score = min(20.0, density * 40.0)

    # 4. Volatility stability score (up to 10 pts)
    stability_score = 10.0 if (0.05 <= cv_price <= 0.80) else 5.0

    final_score = round(volume_score + validity_score + density_score + stability_score, 1)

    if final_score >= 70.0 and unique_dates >= 200:
        recommendation_status = "TIER_1_TRAINING_READY"
    elif final_score >= 50.0 and unique_dates >= 50:
        recommendation_status = "TIER_2_CANDIDATE"
    else:
        recommendation_status = "INSUFFICIENT_DATA"

    return {
        "market": market_name,
        "commodity": commodity,
        "total_records": total_records,
        "unique_sessions": unique_dates,
        "start_date": str(start_date)[:10] if hasattr(start_date, 'date') else str(start_date),
        "end_date": str(end_date)[:10] if hasattr(end_date, 'date') else str(end_date),
        "days_span": days_span,
        "quality_score": final_score,
        "status": recommendation_status
    }


def discover_commodity_markets(
    commodity: str,
    source_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Discover active mandis for a commodity from dataset or current cache.
    """
    config = get_commodity_config(commodity)
    logger.info(f"Starting commodity market discovery for: {config.name}")

    if source_df is None:
        fetcher = CurrentDataFetcher()
        source_df, _, _ = fetcher.fetch_all_current_data(commodity=config.api_commodity_name)

    if source_df.empty:
        logger.warning(f"No market data found for {commodity}.")
        return pd.DataFrame()

    df = source_df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    if "commodity" in df.columns:
        df = df[df["commodity"].str.lower() == commodity.strip().lower()]

    if "market" not in df.columns:
        logger.error("No 'market' column in data.")
        return pd.DataFrame()

    markets = df["market"].unique().tolist()
    logger.info(f"Found {len(markets)} candidate markets reporting for {commodity}.")

    market_evaluations = []
    for m in markets:
        m_df = df[df["market"] == m]
        eval_dict = score_market_quality(m_df, market_name=m, commodity=config.name)
        market_evaluations.append(eval_dict)

    res_df = pd.DataFrame(market_evaluations)
    if not res_df.empty:
        res_df = res_df.sort_values("quality_score", ascending=False).reset_index(drop=True)
        out_file = PROCESSED_DATA_DIR / f"{commodity.strip().lower()}_candidate_markets.csv"
        res_df.to_csv(out_file, index=False)
        logger.info(f"Saved market discovery results to {out_file}")

    return res_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover and score candidate mandis for a commodity.")
    parser.add_argument("--commodity", type=str, default="Potato", help="Target agricultural commodity name")
    args = parser.parse_args()

    results = discover_commodity_markets(commodity=args.commodity)
    if not results.empty:
        print("\n" + "=" * 80)
        print(f"COMMODITY DATA DISCOVERY REPORT: {args.commodity.upper()}")
        print("=" * 80)
        print(results.to_string(index=False))
        print("=" * 80)
    else:
        print(f"No candidate markets discovered for {args.commodity}.")
