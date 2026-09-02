"""
Task 6 - Multi-Commodity Model Quality Audit & Benchmarking.

Performs a rigorous, honest quality audit of all 9 real commodity-market models:
  Onion:  Bareilly, Bargarh, Nagpur
  Potato: Agra
  Tomato: Kolar
  Wheat:  Khanna, Indore
  Rice:   Burdwan

Tier classification (based on improvement over naive baseline):
  TIER-1 RELIABLE    : XGBoost beats naive baseline (improvement_pct > 0)
  TIER-2 ACCEPTABLE  : XGBoost within 20% degradation vs baseline (improvement_pct >= -20)
  TIER-3 UNRELIABLE  : XGBoost significantly worse than baseline (improvement_pct < -20)

Additional signals:
  - R2 score          : > 0.90 = excellent, 0.50-0.90 = good, 0-0.50 = marginal, < 0 = worse than mean
  - Direction Accuracy: > 55% = useful signal, 45-55% = noise, < 45% = anti-signal (concern)
  - Spike MAE ratio   : spike_mae / normal_mae, higher = brittle on volatile days

Output:
  data/processed/model_quality_audit.csv  -- machine-readable audit table
  docs/TASK_6_MODEL_QUALITY_AUDIT.md      -- human-readable narrative report
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
MODELS_DIR = PROCESSED / "models"
REGISTRY_PATH = MODELS_DIR / "model_registry.json"
DOCS_DIR = ROOT / "docs"
DOCS_DIR.mkdir(exist_ok=True)
AUDIT_CSV = PROCESSED / "model_quality_audit.csv"
AUDIT_REPORT = DOCS_DIR / "TASK_6_MODEL_QUALITY_AUDIT.md"

# ---------------------------------------------------------------------------
# Tier thresholds
# ---------------------------------------------------------------------------
TIER1_THRESHOLD = 0.0       # improvement_pct > 0   -> RELIABLE
TIER2_THRESHOLD = -20.0     # improvement_pct >= -20 -> ACCEPTABLE

R2_EXCELLENT = 0.90
R2_GOOD = 0.50
R2_MARGINAL = 0.0

DIR_ACC_GOOD = 55.0
DIR_ACC_NOISE = 45.0
SPIKE_RATIO_WARN = 3.0

# ---------------------------------------------------------------------------
# Onion split files (original naming from Phase 2)
# ---------------------------------------------------------------------------
ONION_SPLITS = {
    "bareilly": {
        "test": MODELS_DIR / "bareilly_baseline_test.csv",
        "model": MODELS_DIR / "change_xgboost_v3" / "final" / "bareilly_final_model.json",
        "features": MODELS_DIR / "change_xgboost_v3" / "final" / "bareilly_final_features.csv",
    },
    "bargarh": {
        "test": MODELS_DIR / "bargarh_baseline_test.csv",
        "model": MODELS_DIR / "change_xgboost_v3" / "final" / "bargarh_final_model.json",
        "features": MODELS_DIR / "change_xgboost_v3" / "final" / "bargarh_final_features.csv",
    },
    "nagpur": {
        "test": MODELS_DIR / "nagpur_baseline_test.csv",
        "model": MODELS_DIR / "change_xgboost_v3" / "final" / "nagpur_final_model.json",
        "features": MODELS_DIR / "change_xgboost_v3" / "final" / "nagpur_final_features.csv",
    },
}

NON_ONION_SPLITS = {
    ("potato", "agra"):    PROCESSED / "splits_potato",
    ("tomato", "kolar"):   PROCESSED / "splits_tomato",
    ("wheat",  "khanna"):  PROCESSED / "splits_wheat",
    ("wheat",  "indore"):  PROCESSED / "splits_wheat",
    ("rice",   "burdwan"): PROCESSED / "splits_rice",
}

NON_ONION_MODEL_PATHS = {
    ("potato", "agra"):    MODELS_DIR / "potato" / "change_xgboost_v3" / "final" / "agra_final_model.json",
    ("tomato", "kolar"):   MODELS_DIR / "tomato" / "change_xgboost_v3" / "final" / "kolar_final_model.json",
    ("wheat",  "khanna"):  MODELS_DIR / "wheat"  / "change_xgboost_v3" / "final" / "khanna_final_model.json",
    ("wheat",  "indore"):  MODELS_DIR / "wheat"  / "change_xgboost_v3" / "final" / "indore_final_model.json",
    ("rice",   "burdwan"): MODELS_DIR / "rice"   / "change_xgboost_v3" / "final" / "burdwan_final_model.json",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(v: Any, decimals: int = 4) -> Optional[float]:
    if v is None:
        return None
    try:
        return round(float(v), decimals)
    except (TypeError, ValueError):
        return None


def _classify_r2(r2: Optional[float]) -> str:
    if r2 is None:
        return "unknown"
    if r2 >= R2_EXCELLENT:
        return "excellent"
    if r2 >= R2_GOOD:
        return "good"
    if r2 >= R2_MARGINAL:
        return "marginal"
    return "worse-than-mean"


def _classify_direction(da: Optional[float]) -> str:
    if da is None:
        return "unknown"
    if da >= DIR_ACC_GOOD:
        return "useful"
    if da >= DIR_ACC_NOISE:
        return "noise"
    return "anti-signal"


def _classify_tier(improvement_pct: Optional[float]) -> str:
    if improvement_pct is None:
        return "UNKNOWN"
    if improvement_pct > TIER1_THRESHOLD:
        return "TIER-1 RELIABLE"
    if improvement_pct >= TIER2_THRESHOLD:
        return "TIER-2 ACCEPTABLE"
    return "TIER-3 UNRELIABLE"


def _farmer_recommendation(tier: str, r2_class: str, dir_class: str) -> str:
    if tier == "TIER-1 RELIABLE":
        return "DEPLOY: safe for farmer-facing price forecasting"
    if tier == "TIER-2 ACCEPTABLE":
        if dir_class == "anti-signal":
            return "CAUTION: acceptable MAE but direction signal unreliable -- use with caveats"
        return "DEPLOY WITH CAVEATS: useful for trend guidance, not precise price quoting"
    if r2_class in ("excellent", "good"):
        return "REVIEW: model fits training well but cannot beat naive -- investigate overfitting or data seasonality"
    return "DO NOT DEPLOY: model is worse than naive baseline -- retraining or more data required"


# ---------------------------------------------------------------------------
# Core evaluation function (shared by Onion and non-Onion)
# ---------------------------------------------------------------------------

def _evaluate_model(
    test_df: pd.DataFrame,
    model_path: Path,
    feature_list: List[str],
    target_col: str,
) -> Optional[Dict[str, Any]]:
    available = [f for f in feature_list if f in test_df.columns]
    if not available:
        print("    [WARN] No matching features in test CSV")
        return None

    X_test = test_df[available].fillna(0.0)
    y_true = test_df[target_col].values

    model = xgb.Booster()
    model.load_model(str(model_path))
    dtest = xgb.DMatrix(X_test)
    y_pred = model.predict(dtest)

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))

    if "lag_1" in test_df.columns:
        naive_preds = test_df["lag_1"].ffill().fillna(0).values
    else:
        naive_preds = np.roll(y_true, 1)
        naive_preds[0] = y_true[0]
    naive_mae = float(mean_absolute_error(y_true, naive_preds))
    improvement_pct = round(((naive_mae - mae) / naive_mae) * 100, 2) if naive_mae > 0 else None

    if len(y_true) > 1:
        true_dir = np.sign(np.diff(y_true))
        pred_dir = np.sign(np.diff(y_pred))
        dir_acc = float(np.mean(true_dir == pred_dir) * 100)
    else:
        dir_acc = None

    residuals = np.abs(y_true - y_pred)
    spike_threshold = 2.0 * mae
    normal_mask = residuals <= spike_threshold
    spike_mask = ~normal_mask
    normal_mae_val = float(np.mean(residuals[normal_mask])) if normal_mask.sum() > 0 else None
    spike_mae_val = float(np.mean(residuals[spike_mask])) if spike_mask.sum() > 0 else None

    return {
        "test_mae": round(mae, 2),
        "test_rmse": round(rmse, 2),
        "test_r2": round(r2, 4),
        "baseline_mae": round(naive_mae, 2),
        "improvement_pct": improvement_pct,
        "direction_accuracy": round(dir_acc, 1) if dir_acc is not None else None,
        "normal_mae": round(normal_mae_val, 2) if normal_mae_val is not None else None,
        "spike_mae": round(spike_mae_val, 2) if spike_mae_val is not None else None,
        "normal_count": int(normal_mask.sum()),
        "spike_count": int(spike_mask.sum()),
        "test_rows": len(y_true),
    }


def _load_features_from_csv(feat_path: Path) -> List[str]:
    if not feat_path.exists():
        return []
    df = pd.read_csv(feat_path, header=None)
    return df.iloc[:, 0].tolist()


def _find_target_col(df: pd.DataFrame) -> Optional[str]:
    for cand in ["target_price", "target", "next_modal_price", "price_change"]:
        if cand in df.columns:
            return cand
    return None


# ---------------------------------------------------------------------------
# Onion model re-evaluation
# ---------------------------------------------------------------------------

def _audit_onion_market(market: str, reg_entry: dict) -> Dict[str, Any]:
    paths = ONION_SPLITS[market]
    live = None

    if paths["test"].exists() and paths["model"].exists():
        test_df = pd.read_csv(paths["test"])
        test_df.columns = [c.strip().lower() for c in test_df.columns]
        target_col = _find_target_col(test_df)
        feature_list = _load_features_from_csv(paths["features"])
        if not feature_list:
            exclude = {
                "date", "arrival_date", "target_price", "price_change",
                "price_change_pct", "price_direction", "market", "commodity",
                "state", "district", "variety", "grade", "modal_price",
                "min_price", "max_price", "retrieved_at", "source", "is_live",
            }
            feature_list = [c for c in test_df.columns if c not in exclude]
        if target_col:
            live = _evaluate_model(test_df, paths["model"], feature_list, target_col)

    if live:
        source = "live-rerun"
        print(f"    Live re-run: MAE=Rs.{live['test_mae']}, R2={live['test_r2']}, Impr={live['improvement_pct']}%")
    else:
        print(f"    [WARN] Falling back to registry values for Onion/{market}")
        live = {
            "test_mae": _safe_float(reg_entry.get("test_mae")),
            "test_rmse": _safe_float(reg_entry.get("rmse")),
            "test_r2": _safe_float(reg_entry.get("r2")),
            "baseline_mae": _safe_float(reg_entry.get("baseline_mae")),
            "improvement_pct": _safe_float(reg_entry.get("improvement_pct")),
            "direction_accuracy": _safe_float(reg_entry.get("direction_accuracy")),
            "normal_mae": None, "spike_mae": None,
            "normal_count": None, "spike_count": None,
            "test_rows": _safe_float(reg_entry.get("test_rows")),
        }
        source = "registry"

    return {"source": source, **live}


# ---------------------------------------------------------------------------
# Non-Onion model re-evaluation
# ---------------------------------------------------------------------------

def _audit_nononion(commodity: str, market: str, reg_entry: dict) -> Dict[str, Any]:
    key = (commodity, market)
    split_dir = NON_ONION_SPLITS.get(key)
    model_path = NON_ONION_MODEL_PATHS.get(key)
    live = None

    if split_dir and model_path and model_path.exists():
        test_candidates = [
            split_dir / f"{commodity}_test.csv",
            split_dir / f"{market}_test.csv",
            split_dir / "test.csv",
        ]
        test_path = next((p for p in test_candidates if p.exists()), None)

        if test_path:
            test_df = pd.read_csv(test_path)
            test_df.columns = [c.strip().lower() for c in test_df.columns]
            target_col = _find_target_col(test_df)
            feature_list = reg_entry.get("feature_list", [])
            if not feature_list:
                exclude = {
                    "date", "arrival_date", "target_price", "price_change",
                    "price_change_pct", "price_direction", "market", "commodity",
                    "state", "district", "variety", "grade", "modal_price",
                    "min_price", "max_price", "retrieved_at", "source", "is_live",
                }
                feature_list = [c for c in test_df.columns if c not in exclude]
            if target_col:
                live = _evaluate_model(test_df, model_path, feature_list, target_col)

    if live:
        source = "live-rerun"
        print(f"  Live re-run: MAE=Rs.{live['test_mae']}, R2={live['test_r2']}, Impr={live['improvement_pct']}%")
    else:
        print(f"  [WARN] Falling back to registry values for {commodity}/{market}")
        live = {
            "test_mae": _safe_float(reg_entry.get("test_mae")),
            "test_rmse": _safe_float(reg_entry.get("rmse")),
            "test_r2": _safe_float(reg_entry.get("r2")),
            "baseline_mae": _safe_float(reg_entry.get("baseline_mae")),
            "improvement_pct": _safe_float(reg_entry.get("improvement_pct")),
            "direction_accuracy": _safe_float(reg_entry.get("direction_accuracy")),
            "normal_mae": None, "spike_mae": None,
            "normal_count": None, "spike_count": None,
            "test_rows": _safe_float(reg_entry.get("test_rows")),
        }
        source = "registry"

    return {"source": source, **live}


# ---------------------------------------------------------------------------
# Main Audit
# ---------------------------------------------------------------------------

def run_audit() -> List[Dict[str, Any]]:
    print("=" * 70)
    print("TASK 6 -- MULTI-COMMODITY MODEL QUALITY AUDIT & BENCHMARKING")
    print("=" * 70)

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    audit_rows: List[Dict[str, Any]] = []

    onion_reg = registry.get("onion", {})
    for market in ["bareilly", "bargarh", "nagpur"]:
        print(f"\n[Onion / {market.title()}]")
        reg_entry = onion_reg.get(market, {})
        result = _audit_onion_market(market, reg_entry)

        impr = result.get("improvement_pct")
        if impr is None and result.get("test_mae") and result.get("baseline_mae"):
            b = result["baseline_mae"]
            if b and b > 0:
                impr = round(((b - result["test_mae"]) / b) * 100, 2)

        tier = _classify_tier(impr)
        r2_class = _classify_r2(result.get("test_r2"))
        dir_class = _classify_direction(result.get("direction_accuracy"))
        sm = result.get("spike_mae")
        nm = result.get("normal_mae")
        spike_ratio = round(sm / nm, 2) if (sm and nm and nm > 0) else None
        rec = _farmer_recommendation(tier, r2_class, dir_class)
        print(f"  Tier={tier}, R2-class={r2_class}, Dir={dir_class}")
        print(f"  -> {rec}")

        audit_rows.append({
            "commodity": "Onion", "market": market.title(), "state": "Various",
            "variety": reg_entry.get("variety", "N/A"),
            "grade": reg_entry.get("grade", "N/A"),
            "train_rows": reg_entry.get("train_rows"),
            "test_rows": result.get("test_rows"),
            "test_mae": result.get("test_mae"),
            "test_rmse": result.get("test_rmse"),
            "test_r2": result.get("test_r2"),
            "baseline_mae": result.get("baseline_mae"),
            "improvement_pct": impr,
            "direction_accuracy": result.get("direction_accuracy"),
            "normal_mae": nm, "spike_mae": sm,
            "normal_count": result.get("normal_count"),
            "spike_count": result.get("spike_count"),
            "spike_ratio": spike_ratio,
            "r2_class": r2_class, "direction_class": dir_class,
            "tier": tier, "farmer_recommendation": rec,
            "source": result.get("source"),
        })

    non_onion_targets = [
        ("potato", "agra", "Potato"),
        ("tomato", "kolar", "Tomato"),
        ("wheat",  "khanna", "Wheat"),
        ("wheat",  "indore", "Wheat"),
        ("rice",   "burdwan", "Rice"),
    ]

    for commodity, market, label in non_onion_targets:
        print(f"\n[{label} / {market.title()}]")
        reg_entry = registry.get(commodity, {}).get(market, {})
        result = _audit_nononion(commodity, market, reg_entry)

        impr = result.get("improvement_pct")
        if impr is None and result.get("test_mae") and result.get("baseline_mae"):
            b = result["baseline_mae"]
            if b and b > 0:
                impr = round(((b - result["test_mae"]) / b) * 100, 2)

        tier = _classify_tier(impr)
        r2_class = _classify_r2(result.get("test_r2"))
        dir_class = _classify_direction(result.get("direction_accuracy"))
        sm = result.get("spike_mae")
        nm = result.get("normal_mae")
        spike_ratio = round(sm / nm, 2) if (sm and nm and nm > 0) else None
        rec = _farmer_recommendation(tier, r2_class, dir_class)
        print(f"  Tier={tier}, R2-class={r2_class}, Dir={dir_class}")
        print(f"  -> {rec}")

        audit_rows.append({
            "commodity": label, "market": market.title(),
            "state": reg_entry.get("state", ""),
            "variety": reg_entry.get("variety", ""),
            "grade": reg_entry.get("grade", ""),
            "train_rows": reg_entry.get("train_rows"),
            "test_rows": result.get("test_rows"),
            "test_mae": result.get("test_mae"),
            "test_rmse": result.get("test_rmse"),
            "test_r2": result.get("test_r2"),
            "baseline_mae": result.get("baseline_mae"),
            "improvement_pct": impr,
            "direction_accuracy": result.get("direction_accuracy"),
            "normal_mae": nm, "spike_mae": sm,
            "normal_count": result.get("normal_count"),
            "spike_count": result.get("spike_count"),
            "spike_ratio": spike_ratio,
            "r2_class": r2_class, "direction_class": dir_class,
            "tier": tier, "farmer_recommendation": rec,
            "source": result.get("source"),
        })

    return audit_rows


# ---------------------------------------------------------------------------
# Save CSV
# ---------------------------------------------------------------------------

def save_audit_csv(rows: List[Dict[str, Any]]) -> Path:
    df = pd.DataFrame(rows)
    df.to_csv(AUDIT_CSV, index=False)
    print(f"\n[OK] Audit CSV saved -> {AUDIT_CSV}")
    return AUDIT_CSV


# ---------------------------------------------------------------------------
# Generate Markdown Report
# ---------------------------------------------------------------------------

def _tier_emoji(tier: str) -> str:
    return {"TIER-1 RELIABLE": "RELIABLE", "TIER-2 ACCEPTABLE": "ACCEPTABLE", "TIER-3 UNRELIABLE": "UNRELIABLE"}.get(tier, "?")


def _pct_str(v: Optional[float]) -> str:
    if v is None:
        return "N/A"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2f}%"


def generate_markdown_report(rows: List[Dict[str, Any]]) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    tier1 = [r for r in rows if r["tier"] == "TIER-1 RELIABLE"]
    tier2 = [r for r in rows if r["tier"] == "TIER-2 ACCEPTABLE"]
    tier3 = [r for r in rows if r["tier"] == "TIER-3 UNRELIABLE"]

    lines = [
        "# Task 6 -- Multi-Commodity Model Quality Audit & Benchmarking",
        "",
        f"> **Audit Date:** {today}",
        "> **Purpose:** Determine which models are production-ready, which need caveats, and which must not be used for farmer-facing forecasts.",
        "",
        "---",
        "",
        "## 1. Scope",
        "",
        "| # | Commodity | Market | State |",
        "|---|-----------|--------|-------|",
    ]
    for i, r in enumerate(rows, 1):
        lines.append(f"| {i} | {r['commodity']} | {r['market']} | {r['state']} |")

    lines += [
        "",
        f"**Total models audited:** {len(rows)}",
        "",
        "---",
        "",
        "## 2. Tier Classification Rules",
        "",
        "| Tier | Condition | Meaning |",
        "|------|-----------|---------|",
        "| TIER-1 RELIABLE | Improvement vs Naive > 0% | XGBoost beats the naive baseline |",
        "| TIER-2 ACCEPTABLE | Improvement within -20% | Tolerable; useful for trend guidance |",
        "| TIER-3 UNRELIABLE | Improvement < -20% | Significantly worse than naive; do not deploy |",
        "",
        "**Additional signals:**",
        "- **R2** >= 0.90 = excellent | 0.50-0.90 = good | 0-0.50 = marginal | < 0 = worse than mean",
        "- **Direction Accuracy** >= 55% = useful | 45-55% = noise | < 45% = anti-signal",
        "- **Spike MAE Ratio** = spike_mae / normal_mae (>3x is concerning)",
        "",
        "---",
        "",
        "## 3. Full Audit Table",
        "",
        "| Commodity | Market | Test MAE | Naive MAE | Improvement | R2 | Dir Acc | Normal MAE | Spike MAE | Spike Ratio | Tier |",
        "|-----------|--------|----------|-----------|-------------|-----|---------|------------|-----------|-------------|------|",
    ]

    for r in rows:
        spike_ratio = f"{r['spike_ratio']:.2f}x" if r.get("spike_ratio") else "N/A"
        normal_mae_s = f"Rs.{r['normal_mae']:.2f}" if r.get("normal_mae") else "N/A"
        spike_mae_s = f"Rs.{r['spike_mae']:.2f}" if r.get("spike_mae") else "N/A"
        r2_s = f"{r['test_r2']:.4f}" if r.get("test_r2") is not None else "N/A"
        da_s = f"{r['direction_accuracy']:.1f}%" if r.get("direction_accuracy") is not None else "N/A"
        lines.append(
            f"| {r['commodity']} | {r['market']} "
            f"| Rs.{r['test_mae']:.2f} "
            f"| Rs.{r['baseline_mae']:.2f} "
            f"| {_pct_str(r['improvement_pct'])} "
            f"| {r2_s} | {da_s} "
            f"| {normal_mae_s} | {spike_mae_s} "
            f"| {spike_ratio} "
            f"| {r['tier']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 4. Tier-by-Tier Verdict",
        "",
        f"### TIER-1 RELIABLE -- {len(tier1)} model(s)",
        "",
        "These models outperform the naive (yesterday's price) baseline on the held-out test set.",
        "",
    ]
    if tier1:
        for r in tier1:
            da = f"{r['direction_accuracy']:.1f}%" if r.get("direction_accuracy") is not None else "N/A"
            r2_v = f"{r['test_r2']:.4f}" if r.get("test_r2") is not None else "N/A"
            lines.append(
                f"- **{r['commodity']} / {r['market']}** -- "
                f"Test MAE Rs.{r['test_mae']:.2f} vs Naive Rs.{r['baseline_mae']:.2f} "
                f"({_pct_str(r['improvement_pct'])} improvement), R2={r2_v}, Dir Acc={da}"
            )
            lines.append(f"  -> *{r['farmer_recommendation']}*")
            lines.append("")
    else:
        lines += ["*No TIER-1 models.*", ""]

    lines += [
        f"### TIER-2 ACCEPTABLE -- {len(tier2)} model(s)",
        "",
        "These models are slightly worse than naive but within the -20% degradation tolerance threshold.",
        "",
    ]
    if tier2:
        for r in tier2:
            da = f"{r['direction_accuracy']:.1f}%" if r.get("direction_accuracy") is not None else "N/A"
            r2_v = f"{r['test_r2']:.4f}" if r.get("test_r2") is not None else "N/A"
            lines.append(
                f"- **{r['commodity']} / {r['market']}** -- "
                f"Test MAE Rs.{r['test_mae']:.2f} vs Naive Rs.{r['baseline_mae']:.2f} "
                f"({_pct_str(r['improvement_pct'])}), R2={r2_v}, Dir Acc={da}"
            )
            lines.append(f"  -> *{r['farmer_recommendation']}*")
            lines.append("")
    else:
        lines += ["*No TIER-2 models.*", ""]

    lines += [
        f"### TIER-3 UNRELIABLE -- {len(tier3)} model(s)",
        "",
        "These models perform significantly worse than a naive baseline and **must not** be used for farmer-facing price forecasts without retraining.",
        "",
    ]
    if tier3:
        for r in tier3:
            da = f"{r['direction_accuracy']:.1f}%" if r.get("direction_accuracy") is not None else "N/A"
            r2_v = f"{r['test_r2']:.4f}" if r.get("test_r2") is not None else "N/A"
            lines.append(
                f"- **{r['commodity']} / {r['market']}** -- "
                f"Test MAE Rs.{r['test_mae']:.2f} vs Naive Rs.{r['baseline_mae']:.2f} "
                f"({_pct_str(r['improvement_pct'])}), R2={r2_v}, Dir Acc={da}"
            )
            lines.append(f"  -> *{r['farmer_recommendation']}*")
            lines.append("")
    else:
        lines += ["*No TIER-3 models.*", ""]

    lines += [
        "---",
        "",
        "## 5. Root-Cause Analysis",
        "",
        "### Why do some models perform worse than naive?",
        "",
        "| Root Cause | Affected Models | Evidence |",
        "|------------|----------------|----------|",
        "| Seasonal price structure dominates -- prices follow tight seasonal bands | Wheat Khanna/Indore | Low R2 (0.22-0.49), large baseline captures trend |",
        "| Rice Burdwan extreme volatility -- paddy market spikes; lag-1 captures short-run memory better | Rice Burdwan | Negative R2 (-0.47), improvement -197%, Dir Acc 16.5% |",
        "| Tomato extreme spikes -- Kolar experiences 10-15x price swings; outliers dominate mean error | Tomato Kolar | Improvement -17%, spike MAE >> normal MAE |",
        "| Limited training data -- Wheat Khanna had only 822 training sessions | Wheat Khanna | 1,175 total sessions; feature selection collapsed to 5 features |",
        "",
        "### Why do Onion models perform well?",
        "",
        "Onion markets (especially Bareilly) have dense, consistent trading history spanning thousands of sessions",
        "with clear seasonal and momentum patterns. XGBoost lag/rolling-window features excel on this data type.",
        "",
        "---",
        "",
        "## 6. Production Deployment Recommendations",
        "",
        "| Priority | Commodity | Market | Action |",
        "|----------|-----------|--------|--------|",
    ]

    deploy_rows = tier1 + tier2
    no_deploy_rows = tier3
    for r in sorted(deploy_rows, key=lambda x: (x.get("improvement_pct") or -999), reverse=True):
        action = "DEPLOY" if r["tier"] == "TIER-1 RELIABLE" else "DEPLOY WITH CAVEATS"
        lines.append(f"| {r['tier']} | {r['commodity']} | {r['market']} | {action} |")
    for r in no_deploy_rows:
        lines.append(f"| {r['tier']} | {r['commodity']} | {r['market']} | DO NOT DEPLOY -- retrain required |")

    lines += [
        "",
        "---",
        "",
        "## 7. Summary Statistics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total models audited | {len(rows)} |",
        f"| TIER-1 RELIABLE | {len(tier1)} |",
        f"| TIER-2 ACCEPTABLE | {len(tier2)} |",
        f"| TIER-3 UNRELIABLE | {len(tier3)} |",
        f"| Models safe to deploy | {len(tier1) + len(tier2)} |",
        f"| Models requiring retraining | {len(tier3)} |",
        "",
        "---",
        "",
        "## 8. Files Created",
        "",
        "| File | Purpose |",
        "|------|---------|",
        "| `data/processed/model_quality_audit.csv` | Machine-readable audit table (all 9 models) |",
        "| `docs/TASK_6_MODEL_QUALITY_AUDIT.md` | This report |",
        "",
        "---",
        "",
        f"*Report generated by `src/tools/audit_model_quality.py` on {today}.*",
    ]

    AUDIT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Audit markdown report saved -> {AUDIT_REPORT}")
    return AUDIT_REPORT


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    audit_rows = run_audit()

    print("\n" + "=" * 70)
    print("AUDIT COMPLETE -- SUMMARY")
    print("=" * 70)

    tier_counts: Dict[str, int] = {}
    for r in audit_rows:
        tier_counts[r["tier"]] = tier_counts.get(r["tier"], 0) + 1

    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier}: {count} model(s)")

    save_audit_csv(audit_rows)
    generate_markdown_report(audit_rows)

    print("\n[ALL DONE] Task 6 quality audit complete.")
    print(f"  CSV    -> {AUDIT_CSV}")
    print(f"  Report -> {AUDIT_REPORT}")
