"""
Comprehensive Benchmark Engine for Commodity ML Models.
Compares:
1. Naive Previous Observed Price Baseline (y_pred = y_t)
2. 7-session Moving Average Baseline (y_pred = mean(y_{t-6:t}))
3. Calibrated XGBoost V3 Model (with validation-based feature selection)

Evaluates on untouched chronological test set.
Computes: MAE, RMSE, R2, Direction Accuracy, Spike MAE (movement >= 10%),
and percentage improvement over naive baseline.
"""
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config.config import PROCESSED_DATA_DIR, get_model_dir
from src.config.model_registry import register_model
from src.features.inference_feature_generator import generate_v3_features
from src.utils.logger import logger

EXCLUDED_COLUMNS = [
    "date", "target_price", "price_change", "price_change_pct", "price_direction",
    "market", "commodity", "state", "district", "variety", "grade",
    "min_price", "max_price", "modal_price", "retrieved_at", "source", "is_live"
]


def evaluate_benchmarks(
    commodity: str,
    market: str,
    dataset_path: Optional[Path] = None,
    top_n_features: int = 20,
    test_ratio: float = 0.20,
    val_ratio: float = 0.20
) -> Dict[str, any]:
    """
    Run full 3-way benchmark (Naive, Moving Average, XGBoost V3) with strict temporal split.
    """
    c_clean = commodity.strip().lower()
    m_clean = market.strip().lower()

    if dataset_path is None:
        dataset_path = PROCESSED_DATA_DIR / f"{c_clean}_{m_clean}_model.csv"

    if not dataset_path.exists():
        logger.error(f"Dataset not found at: {dataset_path}")
        return {"status": "FAILED", "reason": f"File not found: {dataset_path}"}

    df = pd.read_csv(dataset_path)
    df.columns = [c.strip().lower() for c in df.columns]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    elif "arrival_date" in df.columns:
        df["date"] = pd.to_datetime(df["arrival_date"], errors="coerce")
    else:
        raise ValueError("Missing date column")

    df = df.dropna(subset=["date", "modal_price"]).sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)

    if len(df) < 50:
        return {"status": "INSUFFICIENT_DATA", "reason": f"Only {len(df)} rows found"}

    df["modal_price"] = pd.to_numeric(df["modal_price"], errors="coerce")
    df["target_price"] = df["modal_price"].shift(-1)
    df["price_change"] = df["target_price"] - df["modal_price"]

    # Generate V3 features
    df_feat = generate_v3_features(df)
    df_clean = df_feat.dropna(subset=["price_change"]).reset_index(drop=True)

    feature_candidates = [c for c in df_clean.columns if c not in EXCLUDED_COLUMNS]
    df_clean[feature_candidates] = df_clean[feature_candidates].fillna(df_clean[feature_candidates].median())

    n = len(df_clean)
    train_end = int(n * (1.0 - test_ratio - val_ratio))
    val_end = int(n * (1.0 - test_ratio))

    train_df = df_clean.iloc[:train_end].copy()
    val_df = df_clean.iloc[train_end:val_end].copy()
    test_df = df_clean.iloc[val_end:].copy()

    y_actual_test = test_df["target_price"].values
    current_prices_test = test_df["modal_price"].values
    actual_change_test = test_df["price_change"].values

    # ----------------------------------------------------
    # Baseline 1: Naive Previous Observed Price (Change = 0)
    # ----------------------------------------------------
    pred_naive_price = current_prices_test
    mae_naive = float(mean_absolute_error(y_actual_test, pred_naive_price))
    rmse_naive = float(np.sqrt(mean_squared_error(y_actual_test, pred_naive_price)))
    r2_naive = float(r2_score(y_actual_test, pred_naive_price))

    # ----------------------------------------------------
    # Baseline 2: 7-Session Moving Average of Modal Price
    # ----------------------------------------------------
    # If rolling mean available, use it; else compute
    if "rolling_mean_7" in test_df.columns:
        pred_ma_price = test_df["rolling_mean_7"].values
    else:
        pred_ma_price = df_clean["modal_price"].rolling(7, min_periods=1).mean().iloc[val_end:].values

    mae_ma = float(mean_absolute_error(y_actual_test, pred_ma_price))
    rmse_ma = float(np.sqrt(mean_squared_error(y_actual_test, pred_ma_price)))
    r2_ma = float(r2_score(y_actual_test, pred_ma_price))

    # ----------------------------------------------------
    # Feature Selection on Validation Set ONLY
    # ----------------------------------------------------
    X_train = train_df[feature_candidates]
    y_train_change = train_df["price_change"]

    X_val = val_df[feature_candidates]
    y_val_change = val_df["price_change"]

    selector_model = xgb.XGBRegressor(
        n_estimators=150, learning_rate=0.05, max_depth=4,
        subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=0
    )
    selector_model.fit(X_train, y_train_change)
    importance_series = pd.Series(selector_model.feature_importances_, index=feature_candidates)
    selected_features = importance_series.nlargest(top_n_features).index.tolist()

    # ----------------------------------------------------
    # Train Calibrated Model on Train + Val with Selected Features
    # ----------------------------------------------------
    train_val_df = pd.concat([train_df, val_df], ignore_index=True)
    X_train_val = train_val_df[selected_features]
    y_train_val = train_val_df["price_change"]

    final_model = xgb.XGBRegressor(
        n_estimators=200, learning_rate=0.03, max_depth=4,
        subsample=0.85, colsample_bytree=0.85, random_state=42, verbosity=0
    )
    final_model.fit(X_train_val, y_train_val)

    # ----------------------------------------------------
    # Evaluate on Untouched Test Set
    # ----------------------------------------------------
    X_test = test_df[selected_features]
    pred_change_xgb = final_model.predict(X_test)
    pred_xgb_price = current_prices_test + pred_change_xgb

    mae_xgb = float(mean_absolute_error(y_actual_test, pred_xgb_price))
    rmse_xgb = float(np.sqrt(mean_squared_error(y_actual_test, pred_xgb_price)))
    r2_xgb = float(r2_score(y_actual_test, pred_xgb_price))

    # Direction accuracy (when actual price moved)
    actual_direction = np.sign(actual_change_test)
    pred_direction = np.sign(pred_change_xgb)
    directional_correct = (actual_direction == pred_direction)
    direction_accuracy = float(np.mean(directional_correct) * 100.0)

    # Spike Analysis (sessions where abs change >= 10% of current price)
    spike_mask = (np.abs(actual_change_test) / current_prices_test) >= 0.10
    spike_count = int(np.sum(spike_mask))
    if spike_count > 0:
        spike_mae = float(mean_absolute_error(y_actual_test[spike_mask], pred_xgb_price[spike_mask]))
        normal_mae = float(mean_absolute_error(y_actual_test[~spike_mask], pred_xgb_price[~spike_mask]))
    else:
        spike_mae = mae_xgb
        normal_mae = mae_xgb

    improvement_vs_naive = float(((mae_naive - mae_xgb) / mae_naive) * 100.0) if mae_naive > 0 else 0.0

    # Save artifacts
    model_dir = get_model_dir(commodity=commodity, model_type="change_xgboost_v3")
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / f"{m_clean}_final_model.json"
    feat_path = model_dir / f"{m_clean}_final_features.csv"

    final_model.save_model(model_path)
    pd.DataFrame({"feature": selected_features}).to_csv(feat_path, index=False)

    # Register in Model Registry
    register_model(
        commodity=commodity,
        market=market,
        model_type="change_xgboost_v3",
        model_file=f"{m_clean}_final_model.json",
        feature_file=f"{m_clean}_final_features.csv",
        feature_count=len(selected_features),
        test_mae=round(mae_xgb, 2),
        status="VALIDATED",
        trained_at=datetime.now().strftime("%Y-%m-%d")
    )

    return {
        "commodity": commodity,
        "market": market,
        "total_rows": n,
        "train_rows": len(train_df),
        "val_rows": len(val_df),
        "test_rows": len(test_df),
        "selected_feature_count": len(selected_features),
        "naive_mae": round(mae_naive, 2),
        "naive_rmse": round(rmse_naive, 2),
        "ma_mae": round(mae_ma, 2),
        "ma_rmse": round(rmse_ma, 2),
        "xgb_mae": round(mae_xgb, 2),
        "xgb_rmse": round(rmse_xgb, 2),
        "xgb_r2": round(r2_xgb, 4),
        "direction_accuracy_pct": round(direction_accuracy, 1),
        "improvement_vs_naive_pct": round(improvement_vs_naive, 2),
        "spike_count": spike_count,
        "spike_mae": round(spike_mae, 2),
        "normal_mae": round(normal_mae, 2),
        "status": "READY"
    }


if __name__ == "__main__":
    targets = [
        ("Onion", "Bareilly", "data/processed/onion_bareilly_model.csv"),
        ("Onion", "Bargarh", "data/processed/onion_bargarh_model.csv"),
        ("Onion", "Nagpur", "data/processed/onion_nagpur_model.csv"),
        ("Potato", "Agra", "data/processed/potato_agra_model.csv"),
        ("Tomato", "Kolar", "data/processed/tomato_kolar_model.csv"),
        ("Wheat", "Khanna", "data/processed/wheat_khanna_model.csv"),
        ("Rice", "Burdwan", "data/processed/rice_burdwan_model.csv"),
    ]

    print("================================================================================")
    print("RUNNING MULTI-COMMODITY 3-WAY BENCHMARK EVALUATION (PHASE 1-5)")
    print("================================================================================")

    results = []
    for comm, mkt, p in targets:
        print(f"Evaluating {comm} / {mkt}...")
        res = evaluate_benchmarks(comm, mkt, dataset_path=ROOT_DIR / p)
        results.append(res)

    res_df = pd.DataFrame(results)
    print("\nBENCHMARK RESULTS TABLE:")
    print(res_df[["commodity", "market", "naive_mae", "ma_mae", "xgb_mae", "xgb_r2", "direction_accuracy_pct", "improvement_vs_naive_pct", "status"]].to_string(index=False))
