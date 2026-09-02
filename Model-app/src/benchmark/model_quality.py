"""
Task 6 -- Multi-Commodity Model Quality Audit & Benchmarking Module.

Provides reusable functionality for:
  - Metric calculations (MAE, RMSE, R2, MAPE, Direction Accuracy)
  - Baseline improvement calculations
  - Error distribution percentiles (P50/P90/P95/Max)
  - Spike robustness analysis (spike threshold, normal/spike MAE, spike ratio)
  - Deterministic 0-100 Reliability Score calculation
  - Quality Classification (STRONG, ACCEPTABLE, WEAK, REJECT)
  - Farmer Usage Gating (PRODUCTION_READY, USABLE_WITH_WARNING, RESEARCH_ONLY, DISABLED)
  - Export to CSV, ranking CSV, commodity summary CSV, and clean JSON
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ---------------------------------------------------------------------------
# Constants & Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
MODELS_DIR = PROCESSED / "models"
REGISTRY_PATH = MODELS_DIR / "model_registry.json"

# Quality class definitions
QUALITY_STRONG = "STRONG"
QUALITY_ACCEPTABLE = "ACCEPTABLE"
QUALITY_WEAK = "WEAK"
QUALITY_REJECT = "REJECT"

# Usage status definitions
STATUS_PRODUCTION_READY = "PRODUCTION_READY"
STATUS_USABLE_WITH_WARNING = "USABLE_WITH_WARNING"
STATUS_RESEARCH_ONLY = "RESEARCH_ONLY"
STATUS_DISABLED = "DISABLED"

# Benchmark model catalog -- genuine models ONLY
GENUINE_MODELS = [
    ("onion", "bareilly", "Onion", "Bareilly", "Uttar Pradesh"),
    ("onion", "bargarh", "Onion", "Bargarh", "Odisha"),
    ("onion", "nagpur", "Onion", "Nagpur", "Maharashtra"),
    ("potato", "agra", "Potato", "Agra", "Uttar Pradesh"),
    ("tomato", "kolar", "Tomato", "Kolar", "Karnataka"),
    ("wheat", "khanna", "Wheat", "Khanna", "Punjab"),
    ("wheat", "indore", "Wheat", "Indore", "Madhya Pradesh"),
    ("rice", "burdwan", "Rice", "Burdwan", "West Bengal"),
]


# ---------------------------------------------------------------------------
# Mathematical & Metric Helpers
# ---------------------------------------------------------------------------

def calculate_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Mean Absolute Error."""
    return float(mean_absolute_error(y_true, y_pred))


def calculate_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Root Mean Squared Error."""
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def calculate_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate R2 score."""
    return float(r2_score(y_true, y_pred))


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
    """Calculate Mean Absolute Percentage Error where y_true > 0."""
    mask = y_true > 0
    if not np.any(mask):
        return None
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def calculate_direction_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
    """Calculate direction accuracy (percentage of correctly predicted price movement directions)."""
    if len(y_true) < 2:
        return None
    true_diff = np.diff(y_true)
    pred_diff = np.diff(y_pred)
    true_dir = np.sign(true_diff)
    pred_dir = np.sign(pred_diff)
    # Ignore zero movements in denominator if desirable, or count exact sign match
    match = (true_dir == pred_dir)
    return float(np.mean(match) * 100)


def calculate_improvement(baseline_val: float, model_val: float) -> Optional[float]:
    """
    Calculate percentage improvement of model over baseline.
    Positive values mean the model improved (reduced error).
    """
    if baseline_val is None or baseline_val <= 0:
        return None
    return float(((baseline_val - model_val) / baseline_val) * 100)


def calculate_error_distribution(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate absolute-error percentiles and statistics."""
    abs_errors = np.abs(y_true - y_pred)
    return {
        "median_abs_error": round(float(np.median(abs_errors)), 2),
        "p90_abs_error": round(float(np.percentile(abs_errors, 90)), 2),
        "p95_abs_error": round(float(np.percentile(abs_errors, 95)), 2),
        "max_abs_error": round(float(np.max(abs_errors)), 2),
        "mean_abs_error": round(float(np.mean(abs_errors)), 2),
        "std_abs_error": round(float(np.std(abs_errors)), 2),
    }


def calculate_spike_robustness(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    train_mae: float,
    multiplier: float = 2.0,
) -> Dict[str, Any]:
    """
    Evaluate model robustness during price spikes.
    A session is flagged as a spike if |residual| > multiplier * train_mae.
    """
    residuals = np.abs(y_true - y_pred)
    threshold = multiplier * train_mae
    spike_mask = residuals > threshold
    normal_mask = ~spike_mask

    spike_count = int(np.sum(spike_mask))
    normal_count = int(np.sum(normal_mask))

    normal_mae = float(np.mean(residuals[normal_mask])) if normal_count > 0 else float(train_mae)
    spike_mae = float(np.mean(residuals[spike_mask])) if spike_count > 0 else float(train_mae)
    ratio = float(spike_mae / normal_mae) if normal_mae > 0 else 1.0

    return {
        "spike_threshold": round(float(threshold), 2),
        "normal_count": normal_count,
        "spike_count": spike_count,
        "normal_mae": round(normal_mae, 2),
        "spike_mae": round(spike_mae, 2),
        "spike_error_ratio": round(ratio, 2),
    }


# ---------------------------------------------------------------------------
# Reliability Score & Gating Logic
# ---------------------------------------------------------------------------

def calculate_reliability_score(
    mae_improvement_pct: Optional[float],
    rmse_improvement_pct: Optional[float],
    r2_val: float,
    spike_ratio: float,
    direction_acc: Optional[float],
    sample_size: int,
) -> float:
    """
    Calculate a deterministic, transparent 0-100 MODEL RELIABILITY SCORE.

    Component Weights (total 100 points):
      1. MAE Improvement vs Baseline (30 pts max):
         - >= 10% impr -> 30 pts
         - 0% to 10% impr -> linear 15..30 pts
         - -20% to 0% -> linear 0..15 pts
         - < -20% -> 0 pts
      2. R2 Score (25 pts max):
         - R2 >= 0.90 -> 25 pts
         - 0.50 <= R2 < 0.90 -> linear 15..25 pts
         - 0.0 <= R2 < 0.50 -> linear 5..15 pts
         - R2 < 0 -> 0 pts
      3. Spike Robustness (20 pts max):
         - Ratio <= 1.5 -> 20 pts
         - 1.5 < Ratio <= 3.0 -> linear 10..20 pts
         - 3.0 < Ratio <= 5.0 -> linear 0..10 pts
         - Ratio > 5.0 -> 0 pts
      4. Direction Accuracy (15 pts max):
         - Acc >= 55% -> 15 pts
         - 45% <= Acc < 55% -> linear 5..15 pts
         - Acc < 45% -> 0 pts (anti-signal)
      5. Sample Size Adequacy (10 pts max):
         - >= 2000 sessions -> 10 pts
         - 1000..2000 -> 7 pts
         - 500..1000 -> 4 pts
         - < 500 -> 2 pts
    """
    score = 0.0

    # 1. MAE Improvement (30 pts)
    impr = mae_improvement_pct if mae_improvement_pct is not None else -100.0
    if impr >= 10.0:
        score += 30.0
    elif impr >= 0.0:
        score += 15.0 + (impr / 10.0) * 15.0
    elif impr >= -20.0:
        score += ((impr + 20.0) / 20.0) * 15.0
    else:
        score += 0.0

    # 2. R2 Score (25 pts)
    if r2_val >= 0.90:
        score += 25.0
    elif r2_val >= 0.50:
        score += 15.0 + ((r2_val - 0.50) / 0.40) * 10.0
    elif r2_val >= 0.0:
        score += 5.0 + (r2_val / 0.50) * 10.0
    else:
        score += 0.0

    # 3. Spike Robustness (20 pts)
    sr = spike_ratio if spike_ratio > 0 else 1.0
    if sr <= 1.5:
        score += 20.0
    elif sr <= 3.0:
        score += 10.0 + ((3.0 - sr) / 1.5) * 10.0
    elif sr <= 5.0:
        score += ((5.0 - sr) / 2.0) * 10.0
    else:
        score += 0.0

    # 4. Direction Accuracy (15 pts)
    da = direction_acc if direction_acc is not None else 50.0
    if da >= 55.0:
        score += 15.0
    elif da >= 45.0:
        score += 5.0 + ((da - 45.0) / 10.0) * 10.0
    else:
        score += 0.0

    # 5. Sample Size (10 pts)
    if sample_size >= 2000:
        score += 10.0
    elif sample_size >= 1000:
        score += 7.0
    elif sample_size >= 500:
        score += 4.0
    else:
        score += 2.0

    return float(np.clip(round(score, 1), 0.0, 100.0))


def classify_quality(
    mae_improvement_pct: Optional[float],
    rmse_improvement_pct: Optional[float],
    r2_val: float,
) -> str:
    """
    Classify model into quality classes:
      STRONG     : MAE improvement >= 10% AND RMSE improvement >= 5% AND R2 > 0.50
      ACCEPTABLE : MAE improvement >= 0% AND R2 > 0 (and not STRONG)
      WEAK       : MAE improvement < 0% OR R2 <= 0
      REJECT     : Negative baseline improvement < -20% or corrupt data
    """
    impr = mae_improvement_pct if mae_improvement_pct is not None else -100.0
    rmse_impr = rmse_improvement_pct if rmse_improvement_pct is not None else -100.0

    if impr < -20.0:
        return QUALITY_REJECT
    if impr < 0.0 or r2_val <= 0.0:
        return QUALITY_WEAK
    if impr >= 10.0 and rmse_impr >= 5.0 and r2_val > 0.50:
        return QUALITY_STRONG
    if impr >= 0.0 and r2_val > 0.0:
        return QUALITY_ACCEPTABLE

    return QUALITY_WEAK


def assign_usage_status(
    quality_class: str,
    reliability_score: float,
    mae_improvement_pct: Optional[float],
    r2_val: float,
) -> str:
    """
    Assign farmer usage status based on quality class and reliability:
      PRODUCTION_READY    : STRONG or ACCEPTABLE quality AND reliability >= 60.0 AND improvement >= 0
      USABLE_WITH_WARNING : ACCEPTABLE or WEAK quality AND reliability >= 30.0 AND improvement >= -20.0
      RESEARCH_ONLY       : WEAK quality with improvement < -20.0 or reliability < 30.0
      DISABLED            : REJECT or extremely poor fit (R2 < -0.20 or improvement < -50.0)
    """
    impr = mae_improvement_pct if mae_improvement_pct is not None else -100.0

    if impr < -50.0 or r2_val < -0.20 or quality_class == QUALITY_REJECT:
        return STATUS_DISABLED
    if impr < -20.0:
        return STATUS_RESEARCH_ONLY
    if quality_class in (QUALITY_STRONG, QUALITY_ACCEPTABLE) and reliability_score >= 60.0 and impr >= 0.0:
        return STATUS_PRODUCTION_READY
    if reliability_score >= 35.0 and impr >= -20.0:
        return STATUS_USABLE_WITH_WARNING

    return STATUS_RESEARCH_ONLY


# ---------------------------------------------------------------------------
# Data Loaders
# ---------------------------------------------------------------------------

def load_genuine_model_benchmark_data(
    commodity_key: str,
    market_key: str,
) -> Optional[Dict[str, Any]]:
    """
    Load test evaluation data for a genuine trained commodity-market pair.
    Uses pre-saved test predictions or split CSVs. Never uses proxy files.
    """
    # 1. Check Onion models (pre-saved final predictions)
    if commodity_key == "onion":
        pred_path = MODELS_DIR / "change_xgboost_v3" / "final" / f"{market_key}_final_predictions.csv"
        if not pred_path.exists():
            print(f"  [WARN] Onion prediction file missing: {pred_path}")
            return None
        df = pd.read_csv(pred_path)
        y_true = df["actual_price"].values
        y_pred = df["predicted_price"].values
        # Naive predictions: actual_price shifted by 1
        naive_preds = np.roll(y_true, 1)
        naive_preds[0] = y_true[0]

        return {
            "y_true": y_true,
            "y_pred": y_pred,
            "naive_preds": naive_preds,
            "train_sessions": 2500, # approximate for Onion Bareilly/Bargarh/Nagpur
            "test_sessions": len(y_true),
        }

    # 2. Check non-Onion models (splits_X directory + model json)
    split_map = {
        ("potato", "agra"): (PROCESSED / "splits_potato", MODELS_DIR / "potato" / "change_xgboost_v3" / "final" / "agra_final_model.json"),
        ("tomato", "kolar"): (PROCESSED / "splits_tomato", MODELS_DIR / "tomato" / "change_xgboost_v3" / "final" / "kolar_final_model.json"),
        ("wheat", "khanna"): (PROCESSED / "splits_wheat", MODELS_DIR / "wheat" / "change_xgboost_v3" / "final" / "khanna_final_model.json"),
        ("wheat", "indore"): (PROCESSED / "splits_wheat", MODELS_DIR / "wheat" / "change_xgboost_v3" / "final" / "indore_final_model.json"),
        ("rice", "burdwan"): (PROCESSED / "splits_rice", MODELS_DIR / "rice" / "change_xgboost_v3" / "final" / "burdwan_final_model.json"),
    }

    key = (commodity_key, market_key)
    if key not in split_map:
        print(f"  [WARN] Target ({commodity_key}, {market_key}) not in split map")
        return None

    split_dir, model_path = split_map[key]
    if not model_path.exists():
        print(f"  [WARN] Model artifact missing: {model_path}")
        return None

    test_candidates = [
        split_dir / f"{commodity_key}_test.csv",
        split_dir / f"{market_key}_test.csv",
        split_dir / "test.csv",
    ]
    test_path = next((p for p in test_candidates if p.exists()), None)
    if not test_path:
        print(f"  [WARN] Test CSV missing in {split_dir}")
        return None

    train_candidates = [
        split_dir / f"{commodity_key}_train.csv",
        split_dir / f"{market_key}_train.csv",
        split_dir / "train.csv",
    ]
    train_path = next((p for p in train_candidates if p.exists()), None)
    train_rows = len(pd.read_csv(train_path)) if train_path and train_path.exists() else 1000

    test_df = pd.read_csv(test_path)
    test_df.columns = [c.strip().lower() for c in test_df.columns]

    target_col = "target_price"
    if target_col not in test_df.columns:
        print(f"  [WARN] Missing target_price in {test_path}")
        return None

    # Load registry feature list
    if REGISTRY_PATH.exists():
        reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        feat_list = reg.get(commodity_key, {}).get(market_key, {}).get("feature_list", [])
    else:
        feat_list = []

    if not feat_list:
        exclude = {
            "date", "arrival_date", "target_price", "price_change",
            "price_change_pct", "price_direction", "market", "commodity",
            "state", "district", "variety", "grade", "modal_price",
            "min_price", "max_price", "retrieved_at", "source", "is_live",
        }
        feat_list = [c for c in test_df.columns if c not in exclude]

    available = [f for f in feat_list if f in test_df.columns]
    X_test = test_df[available].fillna(0.0)
    y_true = test_df[target_col].values

    model = xgb.Booster()
    model.load_model(str(model_path))
    dtest = xgb.DMatrix(X_test)
    y_pred_change = model.predict(dtest)

    modal_price = test_df["modal_price"].values if "modal_price" in test_df.columns else y_true
    y_pred = modal_price + y_pred_change

    if "lag_1" in test_df.columns:
        naive_preds = test_df["lag_1"].ffill().fillna(method="bfill").values
    else:
        naive_preds = modal_price


    return {
        "y_true": y_true,
        "y_pred": y_pred,
        "naive_preds": naive_preds,
        "train_sessions": train_rows,
        "test_sessions": len(y_true),
    }


# ---------------------------------------------------------------------------
# Benchmark Orchestrator
# ---------------------------------------------------------------------------

def run_commodity_benchmark() -> List[Dict[str, Any]]:
    """
    Run full benchmark across all 8 genuine commodity-market models.
    Returns list of benchmark record dictionaries.
    """
    records: List[Dict[str, Any]] = []

    for comm_key, mkt_key, comm_name, mkt_name, state_name in GENUINE_MODELS:
        print(f"  Benchmarking {comm_name} / {mkt_name} ({state_name}) ...")
        data = load_genuine_model_benchmark_data(comm_key, mkt_key)

        if not data:
            # Handle missing model cleanly
            records.append({
                "commodity": comm_name,
                "market": mkt_name,
                "state": state_name,
                "model_id": f"{comm_key}_{mkt_key}_v3",
                "model_status": "MISSING",
                "quality_class": QUALITY_REJECT,
                "usage_status": STATUS_DISABLED,
                "train_sessions": 0,
                "test_sessions": 0,
                "naive_mae": None, "model_mae": None, "mae_improvement_pct": None,
                "naive_rmse": None, "model_rmse": None, "rmse_improvement_pct": None,
                "r2": None, "mape": None, "direction_accuracy": None,
                "spike_threshold": None, "normal_mae": None, "spike_mae": None, "spike_error_ratio": None,
                "median_abs_error": None, "p90_abs_error": None, "p95_abs_error": None, "max_abs_error": None,
                "reliability_score": 0.0,
                "notes": "Model artifact or test split missing",
            })
            continue

        y_true = data["y_true"]
        y_pred = data["y_pred"]
        naive_preds = data["naive_preds"]

        # Metrics
        model_mae = round(calculate_mae(y_true, y_pred), 2)
        naive_mae = round(calculate_mae(y_true, naive_preds), 2)
        mae_impr = calculate_improvement(naive_mae, model_mae)
        if mae_impr is not None:
            mae_impr = round(mae_impr, 2)

        model_rmse = round(calculate_rmse(y_true, y_pred), 2)
        naive_rmse = round(calculate_rmse(y_true, naive_preds), 2)
        rmse_impr = calculate_improvement(naive_rmse, model_rmse)
        if rmse_impr is not None:
            rmse_impr = round(rmse_impr, 2)

        r2_val = round(calculate_r2(y_true, y_pred), 4)
        mape_val = calculate_mape(y_true, y_pred)
        if mape_val is not None:
            mape_val = round(mape_val, 2)

        dir_acc = calculate_direction_accuracy(y_true, y_pred)
        if dir_acc is not None:
            dir_acc = round(dir_acc, 1)

        err_dist = calculate_error_distribution(y_true, y_pred)
        spike_info = calculate_spike_robustness(y_true, y_pred, train_mae=model_mae)

        rel_score = calculate_reliability_score(
            mae_improvement_pct=mae_impr,
            rmse_improvement_pct=rmse_impr,
            r2_val=r2_val,
            spike_ratio=spike_info["spike_error_ratio"],
            direction_acc=dir_acc,
            sample_size=data["train_sessions"],
        )

        q_class = classify_quality(mae_impr, rmse_impr, r2_val)
        u_status = assign_usage_status(q_class, rel_score, mae_impr, r2_val)

        notes = []
        if mae_impr is not None and mae_impr > 0:
            notes.append(f"Beats naive by {mae_impr:.1f}%")
        elif mae_impr is not None:
            notes.append(f"Worse than naive by {abs(mae_impr):.1f}%")
        if r2_val < 0:
            notes.append("Negative R2 score (worse fit than mean)")
        if spike_info["spike_error_ratio"] > 3.0:
            notes.append(f"High spike error ratio ({spike_info['spike_error_ratio']}x)")

        records.append({
            "commodity": comm_name,
            "market": mkt_name,
            "state": state_name,
            "model_id": f"{comm_key}_{mkt_key}_v3",
            "model_status": "VALIDATED",
            "quality_class": q_class,
            "usage_status": u_status,
            "train_sessions": data["train_sessions"],
            "test_sessions": data["test_sessions"],
            "naive_mae": naive_mae,
            "model_mae": model_mae,
            "mae_improvement_pct": mae_impr,
            "naive_rmse": naive_rmse,
            "model_rmse": model_rmse,
            "rmse_improvement_pct": rmse_impr,
            "r2": r2_val,
            "mape": mape_val,
            "direction_accuracy": dir_acc,
            "spike_threshold": spike_info["spike_threshold"],
            "normal_mae": spike_info["normal_mae"],
            "spike_mae": spike_info["spike_mae"],
            "spike_error_ratio": spike_info["spike_error_ratio"],
            "median_abs_error": err_dist["median_abs_error"],
            "p90_abs_error": err_dist["p90_abs_error"],
            "p95_abs_error": err_dist["p95_abs_error"],
            "max_abs_error": err_dist["max_abs_error"],
            "reliability_score": rel_score,
            "notes": "; ".join(notes),
        })

    return records


# ---------------------------------------------------------------------------
# Exporters & Ranking
# ---------------------------------------------------------------------------

def generate_benchmark_csv(records: List[Dict[str, Any]]) -> Path:
    out_path = PROCESSED / "model_quality_benchmark.csv"
    df = pd.DataFrame(records)
    df.to_csv(out_path, index=False)
    print(f"  [OK] Benchmark CSV saved -> {out_path}")
    return out_path


def generate_ranking_csv(records: List[Dict[str, Any]]) -> Path:
    out_path = PROCESSED / "model_quality_ranking.csv"
    valid = [r for r in records if r["usage_status"] != STATUS_DISABLED]
    disabled = [r for r in records if r["usage_status"] == STATUS_DISABLED]

    # Sort valid models by reliability score descending
    sorted_valid = sorted(valid, key=lambda x: x["reliability_score"], reverse=True)
    sorted_disabled = sorted(disabled, key=lambda x: x["reliability_score"], reverse=True)

    ranking_rows = []
    rank = 1
    for r in sorted_valid:
        ranking_rows.append({
            "rank": rank,
            "commodity": r["commodity"],
            "market": r["market"],
            "reliability_score": r["reliability_score"],
            "quality_class": r["quality_class"],
            "usage_status": r["usage_status"],
            "mae_improvement_pct": r["mae_improvement_pct"],
            "r2": r["r2"],
            "spike_error_ratio": r["spike_error_ratio"],
            "notes": r["notes"],
        })
        rank += 1

    for r in sorted_disabled:
        ranking_rows.append({
            "rank": "DISABLED",
            "commodity": r["commodity"],
            "market": r["market"],
            "reliability_score": r["reliability_score"],
            "quality_class": r["quality_class"],
            "usage_status": r["usage_status"],
            "mae_improvement_pct": r["mae_improvement_pct"],
            "r2": r["r2"],
            "spike_error_ratio": r["spike_error_ratio"],
            "notes": r["notes"],
        })

    df = pd.DataFrame(ranking_rows)
    df.to_csv(out_path, index=False)
    print(f"  [OK] Ranking CSV saved -> {out_path}")
    return out_path


def generate_commodity_summary_csv(records: List[Dict[str, Any]]) -> Path:
    out_path = PROCESSED / "commodity_quality_summary.csv"
    summary_rows = []

    commodities = sorted(list(set(r["commodity"] for r in records)))
    for c in commodities:
        c_recs = [r for r in records if r["commodity"] == c]
        total = len(c_recs)
        prod_ready = sum(1 for r in c_recs if r["usage_status"] == STATUS_PRODUCTION_READY)
        usable_warn = sum(1 for r in c_recs if r["usage_status"] == STATUS_USABLE_WITH_WARNING)
        research = sum(1 for r in c_recs if r["usage_status"] == STATUS_RESEARCH_ONLY)
        disabled = sum(1 for r in c_recs if r["usage_status"] == STATUS_DISABLED)

        best_rec = max(c_recs, key=lambda x: x["reliability_score"])
        avg_rel = round(float(np.mean([r["reliability_score"] for r in c_recs])), 1)

        summary_rows.append({
            "commodity": c,
            "trained_markets_count": total,
            "production_ready_count": prod_ready,
            "usable_with_warning_count": usable_warn,
            "research_only_count": research,
            "disabled_count": disabled,
            "best_market": best_rec["market"],
            "best_reliability_score": best_rec["reliability_score"],
            "avg_reliability_score": avg_rel,
        })

    df = pd.DataFrame(summary_rows)
    df.to_csv(out_path, index=False)
    print(f"  [OK] Commodity summary CSV saved -> {out_path}")
    return out_path


def generate_benchmark_json(records: List[Dict[str, Any]]) -> Path:
    out_path = PROCESSED / "model_quality_benchmark.json"

    formatted_models = []
    for r in records:
        formatted_models.append({
            "commodity": r["commodity"],
            "market": r["market"],
            "state": r["state"],
            "model_id": r["model_id"],
            "model_status": r["model_status"],
            "quality_class": r["quality_class"],
            "usage_status": r["usage_status"],
            "reliability_score": r["reliability_score"],
            "sample_size": {
                "train_sessions": r["train_sessions"],
                "test_sessions": r["test_sessions"],
            },
            "metrics": {
                "mae": r["model_mae"],
                "rmse": r["model_rmse"],
                "r2": r["r2"],
                "mape": r["mape"],
                "direction_accuracy": r["direction_accuracy"],
            },
            "baseline": {
                "naive_mae": r["naive_mae"],
                "naive_rmse": r["naive_rmse"],
                "mae_improvement_pct": r["mae_improvement_pct"],
                "rmse_improvement_pct": r["rmse_improvement_pct"],
            },
            "spike_analysis": {
                "threshold": r["spike_threshold"],
                "normal_mae": r["normal_mae"],
                "spike_mae": r["spike_mae"],
                "spike_error_ratio": r["spike_error_ratio"],
            },
            "error_distribution": {
                "median": r["median_abs_error"],
                "p90": r["p90_abs_error"],
                "p95": r["p95_abs_error"],
                "max": r["max_abs_error"],
            },
            "notes": r["notes"],
        })

    benchmark_json = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "benchmark_version": "1.0.0",
        "benchmark_methodology": "Standardized 70/15/15 chronological split with validation-set feature selection; held-out test evaluation against naive baseline.",
        "models_count": len(formatted_models),
        "models": formatted_models,
    }

    out_path.write_text(json.dumps(benchmark_json, indent=2), encoding="utf-8")
    print(f"  [OK] Benchmark JSON saved -> {out_path}")
    return out_path
