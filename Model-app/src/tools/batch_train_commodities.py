"""
Batch-train only commodities/markets that have genuine historical files
and pass configurable minimum-data gates. Continues after failures.
Supports resume via existing report rows with status VALIDATED.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config.config import MIN_MARKET_TRAINING_SESSIONS, PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.config.model_registry import get_registered_model
from src.data.ingestion.historical_data_fetcher import normalize_historical_frame
from src.tools.train_commodity_model import train_and_select_features
from src.utils.logger import logger


REPORT_COLUMNS = [
    "commodity", "market", "variety", "grade", "quality_score",
    "train_rows", "validation_rows", "test_rows", "feature_count",
    "selected_feature_count", "baseline_mae", "model_mae", "rmse", "r2",
    "direction_accuracy", "improvement_vs_baseline", "status", "reason", "model_path",
]


def discover_genuine_targets() -> List[dict]:
    targets = []
    if not RAW_DATA_DIR.exists():
        return targets
    for path in sorted(RAW_DATA_DIR.glob("*_history.csv")):
        try:
            raw = pd.read_csv(path)
        except Exception:
            continue
        df = normalize_historical_frame(raw)
        if df.empty or "commodity" not in df.columns or "market" not in df.columns:
            continue
        comms = df["commodity"].dropna().astype(str).str.strip().unique()
        markets = df["market"].dropna().astype(str).str.strip().unique()
        if len(comms) != 1 or len(markets) != 1:
            logger.warning(f"Skipping {path.name}: expected one commodity and one market")
            continue
        targets.append({"commodity": comms[0], "market": markets[0], "file": path.name})
    return targets


def run_batch_training(
    min_sessions: int = MIN_MARKET_TRAINING_SESSIONS,
    resume: bool = True,
    include_onion: bool = False,
) -> pd.DataFrame:
    report_path = PROCESSED_DATA_DIR / "batch_training_report.csv"
    existing = pd.DataFrame()
    if resume and report_path.exists():
        existing = pd.read_csv(report_path)

    done = set()
    rows = []
    if not existing.empty:
        for _, rec in existing.iterrows():
            rows.append(rec.to_dict())
            if str(rec.get("status")) == "VALIDATED":
                done.add((str(rec.get("commodity")), str(rec.get("market"))))

    targets = discover_genuine_targets()
    logger.info(f"Batch training found {len(targets)} genuine historical targets.")
    for target in targets:
        comm = target["commodity"]
        market = target["market"]
        if not include_onion and comm.strip().lower() == "onion":
            continue
        if (comm, market) in done:
            logger.info(f"Resume skip VALIDATED {comm}/{market}")
            continue
        registered = get_registered_model(comm, market)
        if resume and registered and str(registered.get("status")) == "VALIDATED":
            logger.info(f"Registry skip VALIDATED {comm}/{market}")
            continue
        logger.info(f"--- Training {comm} / {market} ---")
        try:
            result = train_and_select_features(
                commodity=comm,
                market=market,
                min_sessions=min_sessions,
            )
            result["execution_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rows.append(result)
        except Exception as exc:
            logger.error(f"Batch job {comm}/{market} failed: {exc}")
            rows.append({
                "commodity": comm,
                "market": market,
                "status": "NEEDS_FIX",
                "reason": str(exc),
                "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        pd.DataFrame(rows).to_csv(report_path, index=False)

    report_df = pd.DataFrame(rows)
    if not report_df.empty:
        # Keep latest row per commodity/market
        report_df["_ord"] = range(len(report_df))
        report_df = report_df.sort_values("_ord").drop_duplicates(["commodity", "market"], keep="last")
        report_df = report_df.drop(columns=["_ord"])
    report_df.to_csv(report_path, index=False)
    logger.info(f"Saved batch training report to {report_path}")
    return report_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-sessions", type=int, default=MIN_MARKET_TRAINING_SESSIONS)
    parser.add_argument("--include-onion", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    df = run_batch_training(
        min_sessions=args.min_sessions,
        resume=not args.no_resume,
        include_onion=args.include_onion,
    )
    cols = [c for c in ["commodity", "market", "status", "model_mae", "reason"] if c in df.columns]
    print(df[cols].to_string(index=False) if not df.empty else "No targets")
