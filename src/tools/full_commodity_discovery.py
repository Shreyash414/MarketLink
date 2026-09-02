"""
Full commodity discovery from the official AGMARKNET current catalogue,
merged with any genuine historical downloads already on disk.

A one-day snapshot cannot justify ML training eligibility by itself.
training_eligible is True only when a genuine historical series exists
with at least MIN_MARKET_TRAINING_SESSIONS unique dates.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config.config import (
    MIN_MARKET_TRAINING_SESSIONS,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
)
from src.data.ingestion.historical_data_fetcher import normalize_historical_frame
from src.utils.logger import logger


def _historical_index() -> Dict[str, Dict]:
    index: Dict[str, Dict] = {}
    if not RAW_DATA_DIR.exists():
        return index
    for path in RAW_DATA_DIR.glob("*_history.csv"):
        try:
            raw = pd.read_csv(path)
        except Exception:
            continue
        df = normalize_historical_frame(raw)
        if df.empty or "commodity" not in df.columns:
            continue
        comms = df["commodity"].dropna().astype(str).str.strip().unique()
        if len(comms) != 1:
            continue
        comm = comms[0]
        unique_dates = int(df["date"].nunique()) if "date" in df.columns else 0
        markets = (
            df["market"].dropna().astype(str).str.strip().unique().tolist()
            if "market" in df.columns
            else []
        )
        current = index.get(comm.lower(), {"unique_dates": 0, "markets": set(), "records": 0, "files": []})
        current["unique_dates"] = max(current["unique_dates"], unique_dates)
        current["markets"].update(markets)
        current["records"] += len(df)
        current["files"].append(path.name)
        if "date" in df.columns and df["date"].notna().any():
            start = str(df["date"].min().date())
            end = str(df["date"].max().date())
            current["start_date"] = min(current.get("start_date", start), start)
            current["end_date"] = max(current.get("end_date", end), end)
        index[comm.lower()] = current
    return index


def run_full_commodity_discovery() -> pd.DataFrame:
    raw_file = RAW_DATA_DIR / "mandi_current_raw.csv"
    if not raw_file.exists():
        raise FileNotFoundError(f"Raw catalogue not found at: {raw_file}")

    df_raw = pd.read_csv(raw_file)
    df_raw.columns = [c.strip().lower() for c in df_raw.columns]
    if "commodity" not in df_raw.columns:
        raise KeyError("Official catalogue missing commodity column")

    date_col = next((c for c in ["arrival_date", "date", "reported_date"] if c in df_raw.columns), None)
    if date_col:
        df_raw["parsed_date"] = pd.to_datetime(df_raw[date_col], dayfirst=True, errors="coerce")
    else:
        df_raw["parsed_date"] = pd.NaT

    price_col = "modal_price" if "modal_price" in df_raw.columns else None
    hist = _historical_index()
    commodities = sorted(df_raw["commodity"].dropna().astype(str).str.strip().unique())
    logger.info(f"Discovered {len(commodities)} official AGMARKNET commodity names.")

    report_rows = []
    for comm in commodities:
        sub = df_raw[df_raw["commodity"].astype(str).str.strip() == comm].copy()
        record_count = len(sub)
        markets = sub["market"].dropna().astype(str).str.strip().unique() if "market" in sub.columns else []
        market_count = len(markets)
        valid_dates = sub["parsed_date"].dropna()
        unique_dates = int(valid_dates.nunique())
        start_date = str(valid_dates.min().date()) if not valid_dates.empty else "N/A"
        end_date = str(valid_dates.max().date()) if not valid_dates.empty else "N/A"
        days_span = max(1, (valid_dates.max() - valid_dates.min()).days) if unique_dates > 1 else 1
        observation_density = round(unique_dates / days_span, 3)

        if "market" in sub.columns:
            dups = sub.duplicated(subset=["market", "parsed_date"]).sum()
            dup_rate = round(dups / max(1, record_count), 3)
        else:
            dup_rate = 0.0

        if price_col:
            sub["clean_price"] = pd.to_numeric(sub[price_col], errors="coerce")
            invalid_prices = int(sub["clean_price"].isna().sum() + (sub["clean_price"] <= 0).sum())
            invalid_price_rate = round(invalid_prices / max(1, record_count), 3)
            valid_p = sub["clean_price"][sub["clean_price"] > 0]
            mean_p = float(valid_p.mean()) if len(valid_p) else 0.0
            std_p = float(valid_p.std()) if len(valid_p) > 1 else 0.0
            volatility_cv = round(std_p / mean_p, 3) if mean_p > 0 else 0.0
        else:
            invalid_price_rate = 1.0
            volatility_cv = 0.0

        recent_record_count = record_count
        hist_info = hist.get(comm.lower(), {})
        hist_sessions = int(hist_info.get("unique_dates", 0))
        hist_markets = sorted(hist_info.get("markets", set()))
        candidate_markets = len(hist_markets) if hist_markets else int((sub["market"].value_counts() >= 1).sum()) if "market" in sub.columns else 0

        v_score = min(35.0, (record_count / 300.0) * 35.0)
        m_score = min(25.0, (market_count / 150.0) * 25.0)
        p_score = max(0.0, (1.0 - invalid_price_rate) * 25.0)
        s_score = 15.0 if 0.05 <= volatility_cv <= 0.85 else 7.5
        quality_score = round(v_score + m_score + p_score + s_score, 1)

        if comm.lower() == "onion" and hist_sessions >= MIN_MARKET_TRAINING_SESSIONS:
            status = "VALIDATED"
            training_eligible = True
            reason = "Production-validated genuine multi-year Onion historical series."
        elif hist_sessions >= MIN_MARKET_TRAINING_SESSIONS and invalid_price_rate <= 0.30:
            status = "TESTED" if hist_sessions else "IMPLEMENTED_NOT_TESTED"
            training_eligible = True
            reason = (
                f"Genuine historical files present ({hist_sessions} unique sessions). "
                f"Snapshot-only catalogue cannot train models."
            )
        elif invalid_price_rate > 0.30:
            status = "POOR_DATA_QUALITY"
            training_eligible = False
            reason = f"High invalid price rate ({invalid_price_rate*100:.1f}%) in official snapshot."
        elif hist_sessions and hist_sessions < MIN_MARKET_TRAINING_SESSIONS:
            status = "INSUFFICIENT_DATA"
            training_eligible = False
            reason = f"Historical series has only {hist_sessions} unique sessions (min={MIN_MARKET_TRAINING_SESSIONS})."
        else:
            status = "INSUFFICIENT_DATA"
            training_eligible = False
            reason = (
                "Official current snapshot is a single-day catalogue only; "
                "no genuine multi-session historical file for this commodity."
            )

        if hist_info.get("start_date"):
            start_date = hist_info["start_date"]
            end_date = hist_info["end_date"]
            unique_dates = max(unique_dates, hist_sessions)

        report_rows.append({
            "commodity": comm,
            "api_commodity_name": comm,
            "record_count": record_count if not hist_info else hist_info.get("records", record_count),
            "unique_dates": unique_dates,
            "market_count": market_count,
            "recent_record_count": recent_record_count,
            "start_date": start_date,
            "end_date": end_date,
            "observation_density": observation_density,
            "duplicate_rate": dup_rate,
            "invalid_price_rate": invalid_price_rate,
            "volatility": volatility_cv,
            "quality_score": quality_score,
            "candidate_market_count": candidate_markets,
            "training_eligible": training_eligible,
            "status": status,
            "reason": reason,
        })

    report_df = pd.DataFrame(report_rows).sort_values(
        ["training_eligible", "quality_score", "record_count"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    out_file = PROCESSED_DATA_DIR / "commodity_quality_report.csv"
    report_df.to_csv(out_file, index=False)
    logger.info(f"Saved commodity quality report ({len(report_df)} commodities) to {out_file}")
    return report_df


def build_commodity_catalogue(report_df: pd.DataFrame) -> pd.DataFrame:
    """Derive catalogue rows from official API commodity names only."""
    from src.config.model_registry import load_model_registry

    registry = load_model_registry()
    rows = []
    for _, rec in report_df.iterrows():
        name = rec["api_commodity_name"]
        key = str(name).strip().lower()
        models = registry.get(key, {})
        model_count = len(models)
        candidate_markets = []
        if models:
            candidate_markets = [meta.get("market", mtitle) for mtitle, meta in models.items()]
        rows.append({
            "display_name": name,
            "api_commodity_name": name,
            "status": rec["status"],
            "model_status": "VALIDATED" if model_count and rec["status"] == "VALIDATED" else (
                "VALIDATED" if model_count else "UNTRAINED"
            ),
            "training_eligibility": bool(rec["training_eligible"]),
            "candidate_markets": "|".join(candidate_markets),
            "model_count": model_count,
        })
    catalogue = pd.DataFrame(rows)
    out = PROCESSED_DATA_DIR / "commodity_catalogue.csv"
    catalogue.to_csv(out, index=False)
    logger.info(f"Saved official commodity catalogue ({len(catalogue)} names) to {out}")
    return catalogue


if __name__ == "__main__":
    df_rep = run_full_commodity_discovery()
    build_commodity_catalogue(df_rep)
    print(f"Commodities discovered: {len(df_rep)}")
    print(df_rep["status"].value_counts().to_string())
    print(f"Training eligible: {int(df_rep['training_eligible'].sum())}")
