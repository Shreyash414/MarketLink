"""
Generic Commodity Model Training Pipeline.

Methodology (test set is never used for selection):
TRAIN -> VALIDATION -> select features/model -> TRAIN+VALIDATION -> TEST ONCE
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.config.config import (
    MIN_FEATURE_ROWS,
    MIN_MARKET_TRAINING_SESSIONS,
    MIN_VARIETY_GRADE_OBSERVATIONS,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    get_model_dir,
)
from src.config.model_registry import register_model
from src.data.ingestion.historical_data_fetcher import normalize_historical_frame
from src.data.preprocessing.quality_gate import apply_cleaning_rules, evaluate_series_quality
from src.data.preprocessing.variety_grade import select_variety_grade
from src.features.inference_feature_generator import generate_v3_features
from src.utils.logger import logger


EXCLUDED_COLUMNS = [
    "date",
    "target_price",
    "price_change",
    "price_change_pct",
    "price_direction",
    "market",
    "commodity",
    "state",
    "district",
    "variety",
    "grade",
    "min_price",
    "max_price",
    "modal_price",
    "retrieved_at",
    "source",
    "is_live",
]


def _is_genuine_for_commodity(df: pd.DataFrame, commodity: str) -> bool:
    if df.empty:
        return False
    work = df.copy()
    work.columns = [c.strip().lower() for c in work.columns]
    if "commodity" not in work.columns:
        return False
    values = work["commodity"].dropna().astype(str).str.strip().str.lower().unique().tolist()
    return len(values) == 1 and values[0] == commodity.strip().lower()


def load_commodity_market_dataset(commodity: str, market: str) -> pd.DataFrame:
    """
    Load genuine historical data. Raw official downloads are preferred.
    Relabeled/proxy files whose commodity column does not match are rejected.
    """
    c_clean = commodity.strip().lower()
    m_clean = market.strip().lower().replace(" ", "_")

    paths_to_try = [
        RAW_DATA_DIR / f"{c_clean}_{m_clean}_history.csv",
        PROCESSED_DATA_DIR / f"{c_clean}_{m_clean}_clean.csv",
        PROCESSED_DATA_DIR / f"{c_clean}_{m_clean}_model.csv",
    ]

    for path in paths_to_try:
        if not path.exists():
            continue
        raw = pd.read_csv(path)
        df = normalize_historical_frame(raw) if "arrival_date" in [c.lower() for c in raw.columns] or "Arrival_Date" in raw.columns else raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        if "date" not in df.columns and "arrival_date" in df.columns:
            df["date"] = pd.to_datetime(df["arrival_date"], dayfirst=True, errors="coerce")
        if not _is_genuine_for_commodity(df, commodity):
            logger.warning(
                f"Rejected {path}: commodity column does not uniquely match '{commodity}' (proxy/relabel guard)."
            )
            continue
        logger.info(f"Loaded genuine {commodity} dataset ({len(df)} rows) from {path}")
        return df

    return pd.DataFrame()


def prepare_training_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    date_col = next((c for c in ["date", "arrival_date", "reported_date"] if c in df.columns), None)
    if not date_col:
        raise ValueError("Dataset missing date column.")
    df["date"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)
    if "modal_price" not in df.columns:
        raise ValueError("Dataset missing modal_price column.")
    df["modal_price"] = pd.to_numeric(df["modal_price"], errors="coerce")
    df = df.dropna(subset=["modal_price"]).copy()
    df["target_price"] = df["modal_price"].shift(-1)
    df["price_change"] = df["target_price"] - df["modal_price"]
    df_features = generate_v3_features(df)
    if df_features.empty:
        raise ValueError("Failed to generate V3 features: insufficient historical observations.")
    return df_features.dropna(subset=["price_change"]).reset_index(drop=True)


def train_and_select_features(
    commodity: str,
    market: str,
    top_n_features: int = 20,
    test_ratio: float = 0.20,
    val_ratio: float = 0.20,
    min_sessions: int = MIN_MARKET_TRAINING_SESSIONS,
    min_variety_grade: int = MIN_VARIETY_GRADE_OBSERVATIONS,
) -> Dict:
    """
    Full genuine-data training path with quality gates and variety/grade fallback.
    Feature count/list are selected on TRAIN+VALIDATION importances evaluated on VALIDATION only.
    """
    raw_df = load_commodity_market_dataset(commodity=commodity, market=market)
    if raw_df.empty:
        return {
            "commodity": commodity,
            "market": market,
            "status": "INSUFFICIENT_DATA",
            "reason": "No genuine historical file found (proxy files are rejected)",
        }

    cleaned = apply_cleaning_rules(raw_df)
    selected, vg_report = select_variety_grade(cleaned, min_observations=min_variety_grade)
    if selected.empty:
        return {
            "commodity": commodity,
            "market": market,
            "status": vg_report.get("status", "INSUFFICIENT_DATA"),
            "reason": vg_report.get("reason"),
            "selected_variety": vg_report.get("selected_variety"),
            "selected_grade": vg_report.get("selected_grade"),
        }

    quality = evaluate_series_quality(selected, min_sessions=min_sessions)
    if quality["status"] != "OK":
        return {
            "commodity": commodity,
            "market": market,
            "variety": vg_report.get("selected_variety"),
            "grade": vg_report.get("selected_grade"),
            "quality_score": quality.get("quality_score"),
            "records": quality.get("records"),
            "unique_sessions": quality.get("unique_sessions"),
            "status": quality["status"],
            "reason": quality["reason"],
        }

    try:
        df_full = prepare_training_dataset(selected)
    except Exception as exc:
        return {
            "commodity": commodity,
            "market": market,
            "status": "NEEDS_FIX",
            "reason": str(exc),
        }

    if len(df_full) < MIN_FEATURE_ROWS:
        return {
            "commodity": commodity,
            "market": market,
            "status": "INSUFFICIENT_DATA",
            "reason": f"Only {len(df_full)} feature rows after lag/rolling generation",
        }

    feature_candidates = [c for c in df_full.columns if c not in EXCLUDED_COLUMNS and pd.api.types.is_numeric_dtype(df_full[c])]
    df_full[feature_candidates] = df_full[feature_candidates].fillna(df_full[feature_candidates].median())

    n = len(df_full)
    train_end = int(n * (1.0 - test_ratio - val_ratio))
    val_end = int(n * (1.0 - test_ratio))
    if train_end < 30 or (val_end - train_end) < 10 or (n - val_end) < 10:
        return {
            "commodity": commodity,
            "market": market,
            "status": "INSUFFICIENT_DATA",
            "reason": f"Temporal split too small: n={n}, train_end={train_end}, val_end={val_end}",
        }

    train_df = df_full.iloc[:train_end].copy()
    val_df = df_full.iloc[train_end:val_end].copy()
    test_df = df_full.iloc[val_end:].copy()

    # Feature selection: fit on TRAIN, score importances, keep top N.
    # Validation is used to choose among candidate counts without touching TEST.
    X_train = train_df[feature_candidates]
    y_train = train_df["price_change"]
    selector = xgb.XGBRegressor(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )
    selector.fit(X_train, y_train)
    importance = pd.Series(selector.feature_importances_, index=feature_candidates).sort_values(ascending=False)

    candidate_counts = [n_feat for n_feat in [8, 12, 16, top_n_features, 24] if 4 <= n_feat <= len(feature_candidates)]
    if not candidate_counts:
        candidate_counts = [min(10, len(feature_candidates))]

    best_n = candidate_counts[0]
    best_val_mae = float("inf")
    for n_feat in sorted(set(candidate_counts)):
        feats = importance.nlargest(n_feat).index.tolist()
        model = xgb.XGBRegressor(
            n_estimators=200,
            learning_rate=0.03,
            max_depth=4,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
            verbosity=0,
        )
        model.fit(train_df[feats], train_df["price_change"])
        val_pred = val_df["modal_price"].values + model.predict(val_df[feats])
        val_mae = float(mean_absolute_error(val_df["target_price"].values, val_pred))
        if val_mae < best_val_mae:
            best_val_mae = val_mae
            best_n = n_feat

    selected_features = importance.nlargest(best_n).index.tolist()

    train_val = pd.concat([train_df, val_df], ignore_index=True)
    final_model = xgb.XGBRegressor(
        n_estimators=200,
        learning_rate=0.03,
        max_depth=4,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        verbosity=0,
    )
    final_model.fit(train_val[selected_features], train_val["price_change"])

    pred_changes = final_model.predict(test_df[selected_features])
    predicted_prices = test_df["modal_price"].values + pred_changes
    actual_next = test_df["target_price"].values
    naive_pred = test_df["modal_price"].values

    mae = float(mean_absolute_error(actual_next, predicted_prices))
    rmse = float(np.sqrt(mean_squared_error(actual_next, predicted_prices)))
    r2 = float(r2_score(actual_next, predicted_prices))
    baseline_mae = float(mean_absolute_error(actual_next, naive_pred))
    direction_accuracy = float(np.mean(np.sign(test_df["price_change"].values) == np.sign(pred_changes)) * 100.0)
    improvement = float(((baseline_mae - mae) / baseline_mae) * 100.0) if baseline_mae > 0 else 0.0

    spike_mask = (np.abs(test_df["price_change"].values) / test_df["modal_price"].values) >= 0.10
    spike_mae = (
        float(mean_absolute_error(actual_next[spike_mask], predicted_prices[spike_mask]))
        if spike_mask.any()
        else mae
    )

    model_output_dir = get_model_dir(commodity=commodity, model_type="change_xgboost_v3")
    model_output_dir.mkdir(parents=True, exist_ok=True)
    m_clean = market.strip().lower()
    model_file_name = f"{m_clean}_final_model.json"
    feature_file_name = f"{m_clean}_final_features.csv"
    model_path = model_output_dir / model_file_name
    feature_path = model_output_dir / feature_file_name
    final_model.save_model(model_path)
    pd.DataFrame({"feature": selected_features}).to_csv(feature_path, index=False)

    clean_path = PROCESSED_DATA_DIR / f"{commodity.strip().lower()}_{m_clean}_clean.csv"
    model_csv_path = PROCESSED_DATA_DIR / f"{commodity.strip().lower()}_{m_clean}_model.csv"
    selected.to_csv(clean_path, index=False)
    model_cols = [c for c in ["date", "market", "commodity", "variety", "grade", "min_price", "modal_price", "max_price", "state", "district"] if c in selected.columns]
    selected[model_cols].to_csv(model_csv_path, index=False)

    now_str = datetime.now().strftime("%Y-%m-%d")
    state = selected["state"].iloc[0] if "state" in selected.columns and len(selected) else "N/A"
    district = selected["district"].iloc[0] if "district" in selected.columns and len(selected) else "N/A"
    register_model(
        commodity=commodity,
        market=market,
        model_type="change_xgboost_v3",
        model_file=model_file_name,
        feature_file=feature_file_name,
        feature_count=len(selected_features),
        test_mae=round(mae, 2),
        status="VALIDATED",
        trained_at=now_str,
        state=str(state),
        district=str(district),
        variety=vg_report.get("selected_variety"),
        grade=vg_report.get("selected_grade"),
        rmse=round(rmse, 2),
        r2=round(r2, 4),
        direction_accuracy=round(direction_accuracy, 1),
        baseline_mae=round(baseline_mae, 2),
        improvement_pct=round(improvement, 2),
        train_rows=len(train_df),
        val_rows=len(val_df),
        test_rows=len(test_df),
        model_path=str(model_path),
        feature_list=selected_features,
    )

    return {
        "commodity": commodity,
        "market": market,
        "variety": vg_report.get("selected_variety"),
        "grade": vg_report.get("selected_grade"),
        "quality_score": quality.get("quality_score"),
        "records": quality.get("records"),
        "unique_sessions": quality.get("unique_sessions"),
        "train_rows": len(train_df),
        "validation_rows": len(val_df),
        "test_rows": len(test_df),
        "feature_count": len(feature_candidates),
        "selected_feature_count": len(selected_features),
        "baseline_mae": round(baseline_mae, 2),
        "model_mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 4),
        "direction_accuracy": round(direction_accuracy, 1),
        "improvement_vs_baseline": round(improvement, 2),
        "spike_mae": round(spike_mae, 2),
        "status": "VALIDATED",
        "reason": "Genuine historical series trained with untouched test evaluation",
        "model_path": str(model_path),
        "data_start": quality.get("start_date"),
        "data_end": quality.get("end_date"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train generic commodity XGBoost price model.")
    parser.add_argument("--commodity", type=str, required=True)
    parser.add_argument("--market", type=str, required=True)
    parser.add_argument("--top-n-features", type=int, default=20)
    args = parser.parse_args()
    print(train_and_select_features(commodity=args.commodity, market=args.market, top_n_features=args.top_n_features))
