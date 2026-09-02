"""
Transparent variety/grade selection with ranked fallback.

Never blindly take the modal combination if it is too short.
Minimum observation rule defaults to MIN_VARIETY_GRADE_OBSERVATIONS (60).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.config.config import MIN_VARIETY_GRADE_OBSERVATIONS
from src.utils.logger import logger


def _combo_quality(df: pd.DataFrame) -> Dict[str, Any]:
    work = df.copy()
    n = len(work)
    unique_dates = int(work["date"].nunique()) if "date" in work.columns else n
    prices = pd.to_numeric(work.get("modal_price"), errors="coerce") if "modal_price" in work.columns else pd.Series(dtype=float)
    valid = int((prices > 0).sum()) if len(prices) else 0
    invalid_rate = 1.0 - (valid / max(1, n))
    if "date" in work.columns and unique_dates > 1:
        span = max(1, (work["date"].max() - work["date"].min()).days)
        density = unique_dates / span
    else:
        density = 0.0
    score = round(
        min(40.0, unique_dates / 10.0)
        + max(0.0, (1.0 - invalid_rate) * 40.0)
        + min(20.0, density * 40.0),
        1,
    )
    return {
        "records": n,
        "unique_dates": unique_dates,
        "invalid_price_rate": round(invalid_rate, 4),
        "observation_density": round(density, 4),
        "quality_score": score,
    }


def rank_variety_grade_combinations(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    work = df.copy()
    if "variety" not in work.columns:
        work["variety"] = "UNSPECIFIED"
    if "grade" not in work.columns:
        work["grade"] = "UNSPECIFIED"
    work["variety"] = work["variety"].fillna("UNSPECIFIED").astype(str).str.strip()
    work["grade"] = work["grade"].fillna("UNSPECIFIED").astype(str).str.strip()

    rows = []
    for (variety, grade), sub in work.groupby(["variety", "grade"], dropna=False):
        stats = _combo_quality(sub)
        rows.append({"variety": variety, "grade": grade, **stats})
    ranked = pd.DataFrame(rows)
    if ranked.empty:
        return ranked
    return ranked.sort_values(
        ["unique_dates", "quality_score", "records"],
        ascending=False,
    ).reset_index(drop=True)


def select_variety_grade(
    df: pd.DataFrame,
    min_observations: int = MIN_VARIETY_GRADE_OBSERVATIONS,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Rank all variety+grade combinations and keep the first that meets
    the minimum observation rule. If none qualify, return INSUFFICIENT_DATA.
    """
    ranked = rank_variety_grade_combinations(df)
    report: Dict[str, Any] = {
        "selected_variety": None,
        "selected_grade": None,
        "status": "INSUFFICIENT_DATA",
        "reason": "No variety/grade combinations present",
        "ranked_combinations": ranked.to_dict(orient="records") if not ranked.empty else [],
        "attempts": [],
    }
    if ranked.empty:
        return pd.DataFrame(), report

    work = df.copy()
    if "variety" not in work.columns:
        work["variety"] = "UNSPECIFIED"
    if "grade" not in work.columns:
        work["grade"] = "UNSPECIFIED"
    work["variety"] = work["variety"].fillna("UNSPECIFIED").astype(str).str.strip()
    work["grade"] = work["grade"].fillna("UNSPECIFIED").astype(str).str.strip()

    for _, row in ranked.iterrows():
        variety = str(row["variety"])
        grade = str(row["grade"])
        subset = work[(work["variety"] == variety) & (work["grade"] == grade)].copy()
        n = len(subset)
        attempt = {
            "variety": variety,
            "grade": grade,
            "records": n,
            "unique_dates": int(row["unique_dates"]),
            "quality_score": float(row["quality_score"]),
            "accepted": n >= min_observations,
        }
        report["attempts"].append(attempt)
        if n >= min_observations:
            report.update(
                {
                    "selected_variety": variety,
                    "selected_grade": grade,
                    "status": "SELECTED",
                    "reason": (
                        f"Selected {variety}/{grade} with {n} observations "
                        f"(min={min_observations}); skipped "
                        f"{sum(1 for a in report['attempts'] if not a['accepted'])} weaker combos"
                    ),
                    "records": n,
                    "unique_dates": int(row["unique_dates"]),
                    "quality_score": float(row["quality_score"]),
                }
            )
            logger.info(report["reason"])
            return subset.reset_index(drop=True), report

    best = ranked.iloc[0]
    report.update(
        {
            "selected_variety": str(best["variety"]),
            "selected_grade": str(best["grade"]),
            "status": "INSUFFICIENT_DATA",
            "reason": (
                f"No variety/grade combination reached min_observations={min_observations}. "
                f"Best was {best['variety']}/{best['grade']} with {int(best['records'])} rows."
            ),
        }
    )
    logger.warning(report["reason"])
    return pd.DataFrame(), report
