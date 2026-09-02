"""
Global Multi-Market Model vs Market-Specific Model Experiment.
Investigates whether a single unified XGBoost model pooled across all mandis
with categorical market identifiers can outperform dedicated market-specific models.
Evaluates out-of-sample test error per market.
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

MARKETS = [
    ("Bareilly", "onion_bareilly_model.csv"),
    ("Bargarh", "onion_bargarh_model.csv"),
    ("Nagpur", "onion_nagpur_model.csv"),
]

EXCLUDED_COLUMNS = [
    "date", "target_price", "price_change", "price_change_pct", "price_direction",
    "market", "commodity", "state", "district", "variety", "grade",
    "min_price", "max_price", "modal_price", "retrieved_at", "source", "is_live"
]


def run_global_model_experiment() -> Dict[str, any]:
    # 1. Load and process individual market datasets
    market_dfs = {}
    for mkt_name, f_name in MARKETS:
        p = PROCESSED_DATA_DIR / f_name
        df = pd.read_csv(p)
        df.columns = [c.strip().lower() for c in df.columns]
        df["date"] = pd.to_datetime(df["date"])
        df = df.dropna(subset=["date", "modal_price"]).sort_values("date").drop_duplicates("date").reset_index(drop=True)
        df["target_price"] = df["modal_price"].shift(-1)
        df["price_change"] = df["target_price"] - df["modal_price"]
        
        df_feat = generate_v3_features(df)
        df_clean = df_feat.dropna(subset=["price_change"]).reset_index(drop=True)
        df_clean["market_name"] = mkt_name
        market_dfs[mkt_name] = df_clean

    # 2. Chronological splits per market (60% Train, 20% Val, 20% Test)
    market_splits = {}
    feature_cols = [c for c in list(market_dfs.values())[0].columns if c not in EXCLUDED_COLUMNS and c != "market_name"]

    for mkt_name, df_m in market_dfs.items():
        n = len(df_m)
        tr_end = int(n * 0.60)
        v_end = int(n * 0.80)
        
        train_df = df_m.iloc[:tr_end].copy().fillna(df_m.iloc[:tr_end][feature_cols].median())
        val_df = df_m.iloc[tr_end:v_end].copy().fillna(df_m.iloc[:tr_end][feature_cols].median())
        test_df = df_m.iloc[v_end:].copy().fillna(df_m.iloc[:tr_end][feature_cols].median())
        
        market_splits[mkt_name] = {
            "train": train_df,
            "val": val_df,
            "test": test_df,
            "y_test_actual": test_df["target_price"].values,
            "current_test": test_df["modal_price"].values
        }

    # 3. Market-Specific Models (Baseline comparison)
    specific_results = {}
    for mkt_name, split in market_splits.items():
        m = xgb.XGBRegressor(n_estimators=150, learning_rate=0.05, max_depth=4, random_state=42, verbosity=0)
        m.fit(split["train"][feature_cols], split["train"]["price_change"])
        top_feats = pd.Series(m.feature_importances_, index=feature_cols).nlargest(20).index.tolist()

        m_final = xgb.XGBRegressor(n_estimators=200, learning_rate=0.03, max_depth=4, random_state=42, verbosity=0)
        tr_val = pd.concat([split["train"], split["val"]], ignore_index=True)
        m_final.fit(tr_val[top_feats], tr_val["price_change"])
        
        pred_change = m_final.predict(split["test"][top_feats])
        pred_price = split["current_test"] + pred_change
        mae = float(mean_absolute_error(split["y_test_actual"], pred_price))
        rmse = float(np.sqrt(mean_squared_error(split["y_test_actual"], pred_price)))
        specific_results[mkt_name] = {"mae": round(mae, 2), "rmse": round(rmse, 2)}

    # 4. Train Pooled Global Multi-Market Model
    # Combine training sets and add one-hot market features
    pooled_train = pd.concat([s["train"] for s in market_splits.values()], ignore_index=True)
    pooled_val = pd.concat([s["val"] for s in market_splits.values()], ignore_index=True)
    pooled_tr_val = pd.concat([pooled_train, pooled_val], ignore_index=True)

    # One-hot encoding for market
    one_hot_train = pd.get_dummies(pooled_tr_val["market_name"], prefix="mkt")
    global_feature_cols = feature_cols + list(one_hot_train.columns)
    
    pooled_tr_val_feats = pd.concat([pooled_tr_val[feature_cols].reset_index(drop=True), one_hot_train.reset_index(drop=True)], axis=1)
    
    global_model = xgb.XGBRegressor(
        n_estimators=300, learning_rate=0.03, max_depth=6,
        subsample=0.85, colsample_bytree=0.85, random_state=42, verbosity=0
    )
    global_model.fit(pooled_tr_val_feats, pooled_tr_val["price_change"])

    # 5. Evaluate Global Model on each market's untouched test set
    global_results = {}
    for mkt_name, split in market_splits.items():
        test_df = split["test"]
        # Create one-hot columns for this market
        test_one_hot = pd.DataFrame(0, index=range(len(test_df)), columns=one_hot_train.columns)
        if f"mkt_{mkt_name}" in test_one_hot.columns:
            test_one_hot[f"mkt_{mkt_name}"] = 1
        
        test_feats = pd.concat([test_df[feature_cols].reset_index(drop=True), test_one_hot], axis=1)
        pred_change_g = global_model.predict(test_feats)
        pred_price_g = split["current_test"] + pred_change_g
        
        mae_g = float(mean_absolute_error(split["y_test_actual"], pred_price_g))
        rmse_g = float(np.sqrt(mean_squared_error(split["y_test_actual"], pred_price_g)))
        global_results[mkt_name] = {"mae": round(mae_g, 2), "rmse": round(rmse_g, 2)}

    # Comparison summary
    summary_rows = []
    for mkt_name in market_splits.keys():
        s_mae = specific_results[mkt_name]["mae"]
        g_mae = global_results[mkt_name]["mae"]
        diff_pct = round(((s_mae - g_mae) / s_mae) * 100.0, 2)
        summary_rows.append({
            "market": mkt_name,
            "market_specific_mae": s_mae,
            "global_model_mae": g_mae,
            "global_vs_specific_impr_pct": diff_pct,
            "winner": "GLOBAL" if g_mae < s_mae else "SPECIFIC"
        })

    return {
        "summary": pd.DataFrame(summary_rows),
        "specific_results": specific_results,
        "global_results": global_results
    }


if __name__ == "__main__":
    print("================================================================================")
    print("GLOBAL MULTI-MARKET MODEL EXPERIMENT (PHASE 13)")
    print("================================================================================")
    res = run_global_model_experiment()
    print("\nRESULTS COMPARISON:")
    print(res["summary"].to_string(index=False))
