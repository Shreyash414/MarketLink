"""
External Signals Experiment.
Investigates whether adding:
1. Calendar seasonality features (month, day-of-week, harmonic sin/cos)
2. Neighboring market price indicators (cross-mandi price correlation)
3. Arrival volume proxies (if present in AGMARKNET data)
improves forecast error on validation and untouched test sets.
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


def add_external_seasonality_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "date" in df.columns:
        dt = pd.to_datetime(df["date"])
        # Day of week (0-6)
        df["day_of_week"] = dt.dt.dayofweek
        # Month (1-12)
        df["month"] = dt.dt.month
        # Day of year harmonic cyclics (annual harvest seasonality)
        day_of_year = dt.dt.dayofyear
        df["sin_day_of_year"] = np.sin(2 * np.pi * day_of_year / 365.25)
        df["cos_day_of_year"] = np.cos(2 * np.pi * day_of_year / 365.25)
        # Monthly harmonics
        df["sin_month"] = np.sin(2 * np.pi * dt.dt.month / 12.0)
        df["cos_month"] = np.cos(2 * np.pi * dt.dt.month / 12.0)
    return df


def run_external_signals_experiment() -> Dict[str, any]:
    # Target: Bareilly primary series with Nagpur as neighboring market signal
    bareilly_path = PROCESSED_DATA_DIR / "onion_bareilly_model.csv"
    nagpur_path = PROCESSED_DATA_DIR / "onion_nagpur_model.csv"

    df_b = pd.read_csv(bareilly_path)
    df_b.columns = [c.strip().lower() for c in df_b.columns]
    df_b["date"] = pd.to_datetime(df_b["date"])
    df_b = df_b.dropna(subset=["date", "modal_price"]).sort_values("date").drop_duplicates("date").reset_index(drop=True)

    df_n = pd.read_csv(nagpur_path)
    df_n.columns = [c.strip().lower() for c in df_n.columns]
    df_n["date"] = pd.to_datetime(df_n["date"])
    df_n = df_n.dropna(subset=["date", "modal_price"]).sort_values("date").drop_duplicates("date").reset_index(drop=True)

    # Cross-market merge on date (lagged by 1 day to prevent leakage)
    df_n_lag = df_n[["date", "modal_price"]].copy()
    df_n_lag["nagpur_lag1_price"] = df_n_lag["modal_price"].shift(1)
    df_n_lag["nagpur_lag7_price"] = df_n_lag["modal_price"].shift(7)
    df_n_lag = df_n_lag.drop(columns=["modal_price"])

    df_merged = pd.merge(df_b, df_n_lag, on="date", how="left")
    df_merged["nagpur_lag1_price"] = df_merged["nagpur_lag1_price"].ffill().bfill()
    df_merged["nagpur_lag7_price"] = df_merged["nagpur_lag7_price"].ffill().bfill()

    # Target
    df_merged["target_price"] = df_merged["modal_price"].shift(-1)
    df_merged["price_change"] = df_merged["target_price"] - df_merged["modal_price"]

    # Base features
    df_base = generate_v3_features(df_merged)
    # Base + Seasonality + Cross-Market
    df_ext = add_external_seasonality_features(df_base)

    df_clean = df_ext.dropna(subset=["price_change"]).reset_index(drop=True)

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

    base_cols = [c for c in df_base.columns if c not in excluded and "nagpur" not in c]
    ext_cols = [c for c in df_clean.columns if c not in excluded]

    train_df = train_df.fillna(train_df.median(numeric_only=True))
    val_df = val_df.fillna(train_df.median(numeric_only=True))
    test_df = test_df.fillna(train_df.median(numeric_only=True))

    y_train = train_df["price_change"]
    y_val = val_df["price_change"]
    y_test_actual = test_df["target_price"].values
    current_test = test_df["modal_price"].values

    # Model 1: Base Only
    m_base = xgb.XGBRegressor(n_estimators=150, learning_rate=0.05, max_depth=4, random_state=42, verbosity=0)
    m_base.fit(train_df[base_cols], y_train)
    top_base = pd.Series(m_base.feature_importances_, index=base_cols).nlargest(20).index.tolist()

    m_base_f = xgb.XGBRegressor(n_estimators=200, learning_rate=0.03, max_depth=4, random_state=42, verbosity=0)
    m_base_f.fit(pd.concat([train_df, val_df])[top_base], pd.concat([y_train, y_val]))
    pred_base = current_test + m_base_f.predict(test_df[top_base])
    mae_base = float(mean_absolute_error(y_test_actual, pred_base))

    # Model 2: Base + Seasonality + Cross-Market External Signals
    m_ext = xgb.XGBRegressor(n_estimators=150, learning_rate=0.05, max_depth=4, random_state=42, verbosity=0)
    m_ext.fit(train_df[ext_cols], y_train)
    top_ext = pd.Series(m_ext.feature_importances_, index=ext_cols).nlargest(20).index.tolist()

    m_ext_f = xgb.XGBRegressor(n_estimators=200, learning_rate=0.03, max_depth=4, random_state=42, verbosity=0)
    m_ext_f.fit(pd.concat([train_df, val_df])[top_ext], pd.concat([y_train, y_val]))
    pred_ext = current_test + m_ext_f.predict(test_df[top_ext])
    mae_ext = float(mean_absolute_error(y_test_actual, pred_ext))

    external_features_selected = [f for f in top_ext if f not in base_cols]
    improvement = float(((mae_base - mae_ext) / mae_base) * 100.0)

    return {
        "market": "Bareilly",
        "base_test_mae": round(mae_base, 2),
        "external_signals_test_mae": round(mae_ext, 2),
        "improvement_pct": round(improvement, 2),
        "selected_external_features": external_features_selected
    }


if __name__ == "__main__":
    print("================================================================================")
    print("RUNNING EXTERNAL SIGNALS EXPERIMENT (PHASE 11)")
    print("================================================================================")
    res = run_external_signals_experiment()
    print("\nRESULTS:")
    for k, v in res.items():
        print(f" - {k}: {v}")
