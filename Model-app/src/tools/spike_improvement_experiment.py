"""
Spike Improvement Experiment.
Investigates whether adding dedicated spike-aware and tail-risk features
improves forecasting on large sudden price jumps (>= 10% movement).
Evaluates Normal MAE vs Spike MAE on untouched test sets.
"""
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config.config import PROCESSED_DATA_DIR
from src.features.inference_feature_generator import generate_v3_features
from src.utils.logger import logger


def add_spike_aware_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate additional spike-aware features using strictly historical lookback data.
    """
    df = df.copy()
    p = df["modal_price"]

    # Short-term percentage momentum
    df["momentum_3_pct"] = (p - p.shift(3)) / (p.shift(3) + 1e-5)
    df["momentum_7_pct"] = (p - p.shift(7)) / (p.shift(7) + 1e-5)

    # Rolling volatility ratios
    std_7 = p.rolling(7, min_periods=3).std()
    std_30 = p.rolling(30, min_periods=7).std()
    df["volatility_ratio_7_30"] = std_7 / (std_30 + 1e-5)

    # Normalized position in recent channel [0, 1]
    min_14 = p.rolling(14, min_periods=3).min()
    max_14 = p.rolling(14, min_periods=3).max()
    df["channel_position_14"] = (p - min_14) / (max_14 - min_14 + 1e-5)

    # Distance from recent extreme highs and lows
    df["dist_from_high_14_pct"] = (max_14 - p) / (p + 1e-5)
    df["dist_from_low_14_pct"] = (p - min_14) / (p + 1e-5)

    # Short term acceleration (second derivative of price)
    velocity = p - p.shift(1)
    df["price_acceleration_3"] = velocity - velocity.shift(2)

    # Abnormal jump flag in recent 3 days
    recent_max_jump = (np.abs(p - p.shift(1)) / (p.shift(1) + 1e-5)).rolling(3, min_periods=1).max()
    df["recent_abnormal_jump_flag"] = (recent_max_jump >= 0.08).astype(float)

    return df


def run_spike_experiment(commodity: str, market: str, file_name: str) -> Dict[str, any]:
    file_path = PROCESSED_DATA_DIR / file_name
    df = pd.read_csv(file_path)
    df.columns = [c.strip().lower() for c in df.columns]

    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["date", "modal_price"]).sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)

    df["modal_price"] = pd.to_numeric(df["modal_price"], errors="coerce")
    df["target_price"] = df["modal_price"].shift(-1)
    df["price_change"] = df["target_price"] - df["modal_price"]

    # 1. Base V3 Features
    df_base = generate_v3_features(df)
    # 2. Base + Spike-Aware Features
    df_spike = add_spike_aware_features(df_base)

    df_clean = df_spike.dropna(subset=["price_change"]).reset_index(drop=True)

    n = len(df_clean)
    train_end = int(n * 0.60)
    val_end = int(n * 0.80)

    train_df = df_clean.iloc[:train_end].copy()
    val_df = df_clean.iloc[train_end:val_end].copy()
    test_df = df_clean.iloc[val_end:].copy()

    excluded = [
        "date", "target_price", "price_change", "price_change_pct", "price_direction",
        "market", "commodity", "state", "district", "variety", "grade",
        "min_price", "max_price", "modal_price", "retrieved_at", "source", "is_live"
    ]

    base_feature_cols = [c for c in df_base.columns if c not in excluded]
    all_feature_cols = [c for c in df_clean.columns if c not in excluded]
    spike_only_cols = [c for c in all_feature_cols if c not in base_feature_cols]

    # Fill NaNs
    train_df = train_df.fillna(train_df.median(numeric_only=True))
    val_df = val_df.fillna(train_df.median(numeric_only=True))
    test_df = test_df.fillna(train_df.median(numeric_only=True))

    y_train = train_df["price_change"]
    y_val = val_df["price_change"]
    y_test_change = test_df["price_change"]
    y_test_actual = test_df["target_price"].values
    current_test = test_df["modal_price"].values

    # Model A: Standard V3 (Top 20 selected from base features)
    m_base = xgb.XGBRegressor(n_estimators=150, learning_rate=0.05, max_depth=4, random_state=42, verbosity=0)
    m_base.fit(train_df[base_feature_cols], y_train)
    top_base_feats = pd.Series(m_base.feature_importances_, index=base_feature_cols).nlargest(20).index.tolist()

    m_base_final = xgb.XGBRegressor(n_estimators=200, learning_rate=0.03, max_depth=4, random_state=42, verbosity=0)
    m_base_final.fit(pd.concat([train_df, val_df])[top_base_feats], pd.concat([y_train, y_val]))
    pred_base_price = current_test + m_base_final.predict(test_df[top_base_feats])

    # Model B: Spike-Aware V3 (Top 20 selected from all + spike features)
    m_spike = xgb.XGBRegressor(n_estimators=150, learning_rate=0.05, max_depth=4, random_state=42, verbosity=0)
    m_spike.fit(train_df[all_feature_cols], y_train)
    top_spike_feats = pd.Series(m_spike.feature_importances_, index=all_feature_cols).nlargest(20).index.tolist()

    m_spike_final = xgb.XGBRegressor(n_estimators=200, learning_rate=0.03, max_depth=4, random_state=42, verbosity=0)
    m_spike_final.fit(pd.concat([train_df, val_df])[top_spike_feats], pd.concat([y_train, y_val]))
    pred_spike_price = current_test + m_spike_final.predict(test_df[top_spike_feats])

    # Evaluate on Spikes vs Normal
    spike_mask = (np.abs(y_test_change) / current_test) >= 0.10
    spike_cnt = int(np.sum(spike_mask))

    # Base Metrics
    base_overall_mae = float(mean_absolute_error(y_test_actual, pred_base_price))
    base_spike_mae = float(mean_absolute_error(y_test_actual[spike_mask], pred_base_price[spike_mask])) if spike_cnt > 0 else base_overall_mae
    base_normal_mae = float(mean_absolute_error(y_test_actual[~spike_mask], pred_base_price[~spike_mask])) if spike_cnt < len(test_df) else base_overall_mae

    # Spike-Aware Metrics
    spike_overall_mae = float(mean_absolute_error(y_test_actual, pred_spike_price))
    spike_spike_mae = float(mean_absolute_error(y_test_actual[spike_mask], pred_spike_price[spike_mask])) if spike_cnt > 0 else spike_overall_mae
    spike_normal_mae = float(mean_absolute_error(y_test_actual[~spike_mask], pred_spike_price[~spike_mask])) if spike_cnt < len(test_df) else spike_overall_mae

    spike_mae_impr = float(((base_spike_mae - spike_spike_mae) / base_spike_mae) * 100.0) if base_spike_mae > 0 else 0.0
    overall_mae_impr = float(((base_overall_mae - spike_overall_mae) / base_overall_mae) * 100.0) if base_overall_mae > 0 else 0.0

    selected_spike_feats = [f for f in top_spike_feats if f in spike_only_cols]

    return {
        "commodity": commodity,
        "market": market,
        "test_sessions": len(test_df),
        "spike_sessions": spike_cnt,
        "base_overall_mae": round(base_overall_mae, 2),
        "spike_overall_mae": round(spike_overall_mae, 2),
        "base_spike_mae": round(base_spike_mae, 2),
        "spike_spike_mae": round(spike_spike_mae, 2),
        "base_normal_mae": round(base_normal_mae, 2),
        "spike_normal_mae": round(spike_normal_mae, 2),
        "spike_mae_improvement_pct": round(spike_mae_impr, 2),
        "overall_improvement_pct": round(overall_mae_impr, 2),
        "spike_features_selected": selected_spike_feats
    }


if __name__ == "__main__":
    targets = [
        ("Onion", "Bareilly", "onion_bareilly_model.csv"),
        ("Onion", "Bargarh", "onion_bargarh_model.csv"),
        ("Onion", "Nagpur", "onion_nagpur_model.csv"),
    ]

    print("================================================================================")
    print("RUNNING SPIKE IMPROVEMENT EXPERIMENT (PHASE 10)")
    print("================================================================================")

    res_list = []
    for comm, mkt, f in targets:
        r = run_spike_experiment(comm, mkt, f)
        res_list.append(r)

    res_df = pd.DataFrame(res_list)
    print("\nSPIKE EXPERIMENT RESULTS:")
    print(res_df[["commodity", "market", "spike_sessions", "base_spike_mae", "spike_spike_mae", "spike_mae_improvement_pct", "base_overall_mae", "spike_overall_mae", "overall_improvement_pct"]].to_string(index=False))
    
    print("\nSPIKE FEATURES SELECTED IN TOP 20:")
    for r in res_list:
        print(f" - {r['commodity']} {r['market']}: {r['spike_features_selected']}")
