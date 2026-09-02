"""
Pre-training data quality gates. Never train silently on corrupted series.
"""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from src.config.config import (
    MAX_DUPLICATE_RATE,
    MAX_GAP_DAYS_RATIO,
    MAX_INVALID_PRICE_RATE,
    MIN_MARKET_TRAINING_SESSIONS,
)


def evaluate_series_quality(
    df: pd.DataFrame,
    min_sessions: int = MIN_MARKET_TRAINING_SESSIONS,
) -> Dict[str, Any]:
    issues: List[str] = []
    if df is None or df.empty:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "Empty dataset",
            "records": 0,
            "unique_sessions": 0,
            "quality_score": 0.0,
            "issues": ["empty"],
        }

    work = df.copy()
    work.columns = [c.strip().lower() for c in work.columns]
    if "date" not in work.columns:
        return {
            "status": "POOR_DATA_QUALITY",
            "reason": "Missing date column",
            "records": len(work),
            "unique_sessions": 0,
            "quality_score": 0.0,
            "issues": ["missing_date"],
        }

    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    impossible_dates = int(work["date"].isna().sum())
    if impossible_dates:
        issues.append(f"impossible_dates={impossible_dates}")
    work = work.dropna(subset=["date"])

    records = len(work)
    unique_sessions = int(work["date"].nunique())
    dup_date_rate = 1.0 - (unique_sessions / max(1, records))
    exact_dup_rate = float(work.duplicated().mean()) if records else 1.0

    if "modal_price" not in work.columns:
        issues.append("missing_modal_price")
        prices = pd.Series(dtype=float)
    else:
        prices = pd.to_numeric(work["modal_price"], errors="coerce")

    missing_prices = int(prices.isna().sum()) if len(prices) else records
    negative_prices = int((prices < 0).sum()) if len(prices) else 0
    nonpositive = int((prices <= 0).sum()) if len(prices) else records
    invalid_price_rate = nonpositive / max(1, records)

    min_gt_modal = modal_gt_max = 0
    if "min_price" in work.columns:
        min_p = pd.to_numeric(work["min_price"], errors="coerce")
        min_gt_modal = int(((min_p > prices) & min_p.notna() & prices.notna() & (min_p > 0)).sum())
    if "max_price" in work.columns:
        max_p = pd.to_numeric(work["max_price"], errors="coerce")
        modal_gt_max = int(((prices > max_p) & max_p.notna() & prices.notna() & (max_p > 0)).sum())
        # Official dump sometimes stores 0 min/max with a valid modal; that is incomplete, not fatal.
    if min_gt_modal:
        issues.append(f"min_gt_modal={min_gt_modal}")
    if modal_gt_max:
        issues.append(f"modal_gt_max={modal_gt_max}")
    if missing_prices:
        issues.append(f"missing_prices={missing_prices}")
    if negative_prices:
        issues.append(f"negative_prices={negative_prices}")
    if exact_dup_rate > 0:
        issues.append(f"exact_duplicate_rate={exact_dup_rate:.3f}")
    if dup_date_rate > 0:
        issues.append(f"duplicate_session_rate={dup_date_rate:.3f}")

    start = work["date"].min() if unique_sessions else None
    end = work["date"].max() if unique_sessions else None
    span_days = int((end - start).days) if start is not None and end is not None else 0
    density = unique_sessions / max(1, span_days)
    gap_ratio = 1.0 - density
    if gap_ratio > MAX_GAP_DAYS_RATIO and unique_sessions < min_sessions * 2:
        issues.append(f"excessive_gaps gap_ratio={gap_ratio:.3f}")

    valid_prices = prices[prices > 0]
    mean_p = float(valid_prices.mean()) if len(valid_prices) else 0.0
    std_p = float(valid_prices.std()) if len(valid_prices) > 1 else 0.0
    volatility = (std_p / mean_p) if mean_p > 0 else 0.0

    volume_score = min(40.0, (unique_sessions / float(min_sessions)) * 40.0)
    validity_score = max(0.0, (1.0 - invalid_price_rate) * 30.0)
    density_score = min(20.0, density * 40.0)
    stability_score = 10.0 if 0.02 <= volatility <= 1.2 else 4.0
    quality_score = round(volume_score + validity_score + density_score + stability_score, 1)

    status = "OK"
    reason = "Series passed quality gates"
    if unique_sessions < min_sessions:
        status = "INSUFFICIENT_DATA"
        reason = f"Only {unique_sessions} unique sessions (min={min_sessions})"
    elif invalid_price_rate > MAX_INVALID_PRICE_RATE:
        status = "POOR_DATA_QUALITY"
        reason = f"Invalid-price rate {invalid_price_rate:.3f} exceeds {MAX_INVALID_PRICE_RATE}"
    elif exact_dup_rate > MAX_DUPLICATE_RATE and unique_sessions < min_sessions:
        status = "POOR_DATA_QUALITY"
        reason = f"Duplicate rate {exact_dup_rate:.3f} exceeds {MAX_DUPLICATE_RATE}"
    elif nonpositive == records:
        status = "POOR_DATA_QUALITY"
        reason = "All modal prices missing or non-positive"
    elif quality_score < 35:
        status = "POOR_DATA_QUALITY"
        reason = f"Quality score {quality_score} below minimum usable threshold"

    return {
        "status": status,
        "reason": reason,
        "records": records,
        "unique_sessions": unique_sessions,
        "start_date": str(start.date()) if start is not None else None,
        "end_date": str(end.date()) if end is not None else None,
        "observation_density": round(density, 4),
        "duplicate_rate": round(dup_date_rate, 4),
        "invalid_price_rate": round(invalid_price_rate, 4),
        "volatility": round(volatility, 4),
        "quality_score": quality_score,
        "issues": issues,
        "min_gt_modal": min_gt_modal,
        "modal_gt_max": modal_gt_max,
    }


def apply_cleaning_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Drop unusable rows while keeping official zeros in min/max if modal is valid."""
    work = df.copy()
    work.columns = [c.strip().lower() for c in work.columns]
    if "date" in work.columns:
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        work = work.dropna(subset=["date"])
    if "modal_price" in work.columns:
        work["modal_price"] = pd.to_numeric(work["modal_price"], errors="coerce")
        work = work[work["modal_price"] > 0]
    for col in ["min_price", "max_price"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.drop_duplicates()
    if "date" in work.columns:
        work = work.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return work.reset_index(drop=True)
