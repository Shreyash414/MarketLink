"""
Task 4 — Real Wheat ML Model Training, Feature Selection, Evaluation & Validation.
Executed strictly on genuine AGMARKNET history for Khanna (Punjab) and Indore (Madhya Pradesh).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.config.commodity_registry import get_commodity_config, register_commodity_config
from src.config.config import MIN_FEATURE_ROWS, MIN_MARKET_TRAINING_SESSIONS, PROCESSED_DATA_DIR, RAW_DATA_DIR, get_model_dir
from src.config.model_registry import register_model
from src.data.preprocessing.quality_gate import apply_cleaning_rules, evaluate_series_quality
from src.data.preprocessing.variety_grade import rank_variety_grade_combinations, select_variety_grade
from src.features.inference_feature_generator import generate_v3_features
from src.models.model_predictor import ModelPredictor
from src.recommendation.mandi_recommender import MandiRecommender
from src.risk.risk_engine import RiskEngine
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

TARGET_MARKETS = [
    {"market": "Khanna", "state": "Punjab", "district": "Ludhiana", "file": "wheat_khanna_history.csv", "coords": (30.7046, 76.2166)},
    {"market": "Indore", "state": "Madhya Pradesh", "district": "Indore", "file": "wheat_indore_history.csv", "coords": (22.7196, 75.8577)},
]


def profile_and_train_wheat_market(market_info: Dict[str, Any]) -> Dict[str, Any]:
    market = market_info["market"]
    state = market_info["state"]
    district = market_info["district"]
    file_name = market_info["file"]
    m_clean = market.strip().lower()

    print(f"\n==================================================")
    print(f"PROCESSING WHEAT MARKET: {market} ({state})")
    print(f"==================================================")

    # ----------------------------------------------------
    # Step 3: Profile Wheat Data
    # ----------------------------------------------------
    raw_path = RAW_DATA_DIR / file_name
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing genuine raw history: {raw_path}")

    raw_df = pd.read_csv(raw_path)
    raw_df.columns = [c.strip().lower() for c in raw_df.columns]

    raw_df["date"] = pd.to_datetime(raw_df["arrival_date"], dayfirst=True, errors="coerce")
    raw_df["modal_price"] = pd.to_numeric(raw_df["modal_price"], errors="coerce")
    raw_df["min_price"] = pd.to_numeric(raw_df["min_price"], errors="coerce")
    raw_df["max_price"] = pd.to_numeric(raw_df["max_price"], errors="coerce")

    total_rows = len(raw_df)
    unique_dates = int(raw_df["date"].nunique())
    start_date = str(raw_df["date"].min().date())
    end_date = str(raw_df["date"].max().date())
    dup_rows = int(raw_df.duplicated().sum())
    missing_modal = int(raw_df["modal_price"].isna().sum())
    invalid_dates = int(raw_df["date"].isna().sum())
    negative_prices = int((raw_df["modal_price"] < 0).sum())

    min_gt_modal = int(
        ((raw_df["min_price"] > raw_df["modal_price"]) & (raw_df["min_price"] > 0) & (raw_df["modal_price"] > 0)).sum()
    )
    modal_gt_max = int(
        ((raw_df["modal_price"] > raw_df["max_price"]) & (raw_df["max_price"] > 0) & (raw_df["modal_price"] > 0)).sum()
    )
    min_gt_max = int(
        ((raw_df["min_price"] > raw_df["max_price"]) & (raw_df["min_price"] > 0) & (raw_df["max_price"] > 0)).sum()
    )

    varieties_count = int(raw_df["variety"].nunique())
    grades_count = int(raw_df["grade"].nunique())

    profile_rows = [
        {"metric": "total_rows", "value": total_rows},
        {"metric": "unique_dates", "value": unique_dates},
        {"metric": "start_date", "value": start_date},
        {"metric": "end_date", "value": end_date},
        {"metric": "duplicate_rows", "value": dup_rows},
        {"metric": "missing_modal_prices", "value": missing_modal},
        {"metric": "invalid_dates", "value": invalid_dates},
        {"metric": "negative_prices", "value": negative_prices},
        {"metric": "min_gt_modal_count", "value": min_gt_modal},
        {"metric": "modal_gt_max_count", "value": modal_gt_max},
        {"metric": "min_gt_max_count", "value": min_gt_max},
        {"metric": "varieties_count", "value": varieties_count},
        {"metric": "grades_count", "value": grades_count},
    ]

    profile_df = pd.DataFrame(profile_rows)
    profile_df.to_csv(PROCESSED_DATA_DIR / f"wheat_{m_clean}_data_profile.csv", index=False)
    print(f"Step 3 Complete: Profile saved for {market} ({total_rows} rows, {unique_dates} unique dates)")

    # ----------------------------------------------------
    # Step 4: Variety / Grade Selection
    # ----------------------------------------------------
    cleaned_raw = apply_cleaning_rules(raw_df)
    selected_df, vg_report = select_variety_grade(cleaned_raw, min_observations=60)

    if selected_df.empty:
        return {
            "commodity": "Wheat",
            "market": market,
            "state": state,
            "status": "INSUFFICIENT_DATA",
            "reason": f"Variety/Grade selection failed: {vg_report.get('reason')}",
        }

    sel_variety = vg_report["selected_variety"]
    sel_grade = vg_report["selected_grade"]
    raw_obs = len(selected_df)
    sel_dates = int(selected_df["date"].nunique())

    print(f"Step 4 Complete: Variety={sel_variety}, Grade={sel_grade}, Obs={raw_obs}, Dates={sel_dates}")

    # ----------------------------------------------------
    # Step 5: Quality Gate
    # ----------------------------------------------------
    quality = evaluate_series_quality(selected_df, min_sessions=MIN_MARKET_TRAINING_SESSIONS)
    if quality["status"] != "OK":
        print(f"Quality gate warning for {market}: {quality['reason']}")
        if quality["unique_sessions"] < MIN_MARKET_TRAINING_SESSIONS:
            return {
                "commodity": "Wheat",
                "market": market,
                "state": state,
                "status": quality["status"],
                "reason": quality["reason"],
            }

    print(f"Step 5 Complete: Quality Gate Score={quality['quality_score']}, Sessions={quality['unique_sessions']}")

    # ----------------------------------------------------
    # Step 6: Create Clean Model Dataset
    # ----------------------------------------------------
    clean_model_path = PROCESSED_DATA_DIR / f"wheat_{m_clean}_model.csv"
    clean_path = PROCESSED_DATA_DIR / f"wheat_{m_clean}_clean.csv"
    selected_df.to_csv(clean_path, index=False)

    model_cols = [
        c
        for c in ["date", "market", "commodity", "variety", "grade", "min_price", "modal_price", "max_price", "state", "district"]
        if c in selected_df.columns
    ]
    selected_df[model_cols].to_csv(clean_model_path, index=False)
    print(f"Step 6 Complete: Saved clean dataset ({len(selected_df)} rows) to {clean_model_path}")

    # ----------------------------------------------------
    # Step 7: V3 Feature Engineering
    # ----------------------------------------------------
    work_df = selected_df.copy()
    work_df["target_price"] = work_df["modal_price"].shift(-1)
    work_df["price_change"] = work_df["target_price"] - work_df["modal_price"]

    df_v3 = generate_v3_features(work_df)
    df_v3 = df_v3.dropna(subset=["price_change"]).reset_index(drop=True)

    feats_dir = PROCESSED_DATA_DIR / "features"
    feats_dir.mkdir(parents=True, exist_ok=True)
    v3_path = feats_dir / f"wheat_{m_clean}_features_v3.csv"
    df_v3.to_csv(v3_path, index=False)
    print(f"Step 7 Complete: V3 Features saved to {v3_path} ({len(df_v3)} rows)")

    # ----------------------------------------------------
    # Step 8: Chronological Train / Val / Test Split (70/15/15)
    # ----------------------------------------------------
    n = len(df_v3)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    train_df = df_v3.iloc[:train_end].copy()
    val_df = df_v3.iloc[train_end:val_end].copy()
    test_df = df_v3.iloc[val_end:].copy()

    splits_dir = PROCESSED_DATA_DIR / "splits_wheat"
    splits_dir.mkdir(parents=True, exist_ok=True)

    train_df.to_csv(splits_dir / f"{m_clean}_train.csv", index=False)
    val_df.to_csv(splits_dir / f"{m_clean}_validation.csv", index=False)
    test_df.to_csv(splits_dir / f"{m_clean}_test.csv", index=False)

    assert train_df["date"].max() < val_df["date"].min(), "Train/Val overlap!"
    assert val_df["date"].max() < test_df["date"].min(), "Val/Test overlap!"

    print(f"Step 8 Complete: Chronological splits created (Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)})")

    # ----------------------------------------------------
    # Step 9: Baseline Evaluation
    # ----------------------------------------------------
    val_actual = val_df["target_price"].values
    val_current = val_df["modal_price"].values

    test_actual = test_df["target_price"].values
    test_current = test_df["modal_price"].values
    test_naive_mae = float(mean_absolute_error(test_actual, test_current))
    test_naive_rmse = float(np.sqrt(mean_squared_error(test_actual, test_current)))
    test_naive_mape = float(np.mean(np.abs((test_actual - test_current) / test_actual)) * 100.0)

    test_roll7 = test_df["rolling_mean_7"].values if "rolling_mean_7" in test_df.columns else test_current
    test_roll7_mae = float(mean_absolute_error(test_actual, test_roll7))

    print(f"Step 9 Complete: Naive Test MAE={test_naive_mae:.2f}, RMSE={test_naive_rmse:.2f}, MAPE={test_naive_mape:.2f}%")

    # ----------------------------------------------------
    # Step 10-11: XGBoost & Feature Selection (Validation Set ONLY)
    # ----------------------------------------------------
    feature_candidates = [
        c for c in df_v3.columns if c not in EXCLUDED_COLUMNS and pd.api.types.is_numeric_dtype(df_v3[c])
    ]
    train_df[feature_candidates] = train_df[feature_candidates].fillna(train_df[feature_candidates].median())
    val_df[feature_candidates] = val_df[feature_candidates].fillna(train_df[feature_candidates].median())
    test_df[feature_candidates] = test_df[feature_candidates].fillna(train_df[feature_candidates].median())

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

    candidate_counts = [5, 10, 15, 20, 30, 40, 50, len(feature_candidates)]
    candidate_counts = sorted(list(set([n_feat for n_feat in candidate_counts if 3 <= n_feat <= len(feature_candidates)])))

    val_selection_results = []
    best_n = candidate_counts[0]
    best_val_mae = float("inf")

    for n_feat in candidate_counts:
        top_feats = importance.nlargest(n_feat).index.tolist()
        model_cand = xgb.XGBRegressor(
            n_estimators=200,
            learning_rate=0.03,
            max_depth=4,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
            verbosity=0,
        )
        model_cand.fit(train_df[top_feats], train_df["price_change"])
        cand_val_pred = val_df["modal_price"].values + model_cand.predict(val_df[top_feats])
        cand_val_mae = float(mean_absolute_error(val_actual, cand_val_pred))

        val_selection_results.append({"market": market, "feature_count": n_feat, "val_mae": round(cand_val_mae, 2)})
        if cand_val_mae < best_val_mae:
            best_val_mae = cand_val_mae
            best_n = n_feat

    selected_features = importance.nlargest(best_n).index.tolist()
    print(f"Step 10-11 Complete: Selected top {best_n} features based on Validation MAE ({best_val_mae:.2f})")

    # ----------------------------------------------------
    # Step 12: Retrain on Train+Validation & Test ONCE
    # ----------------------------------------------------
    train_val_df = pd.concat([train_df, val_df], ignore_index=True)
    final_model = xgb.XGBRegressor(
        n_estimators=200,
        learning_rate=0.03,
        max_depth=4,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        verbosity=0,
    )
    final_model.fit(train_val_df[selected_features], train_val_df["price_change"])

    test_pred_changes = final_model.predict(test_df[selected_features])
    test_predicted_prices = test_current + test_pred_changes

    test_mae = float(mean_absolute_error(test_actual, test_predicted_prices))
    test_rmse = float(np.sqrt(mean_squared_error(test_actual, test_predicted_prices)))
    test_r2 = float(r2_score(test_actual, test_predicted_prices))
    test_mape = float(np.mean(np.abs((test_actual - test_predicted_prices) / test_actual)) * 100.0)
    direction_acc = float(np.mean(np.sign(test_df["price_change"].values) == np.sign(test_pred_changes)) * 100.0)
    improvement_pct = float(((test_naive_mae - test_mae) / test_naive_mae) * 100.0)

    print(f"Step 12 Complete: Test Evaluation ONCE:")
    print(f"  Test MAE: {test_mae:.2f} (vs Naive {test_naive_mae:.2f}) -> {improvement_pct:+.2f}% improvement")
    print(f"  Test RMSE: {test_rmse:.2f}, R2: {test_r2:.4f}, MAPE: {test_mape:.2f}%, Direction Acc: {direction_acc:.1f}%")

    # ----------------------------------------------------
    # Step 13: Error Analysis
    # ----------------------------------------------------
    errors = test_predicted_prices - test_actual
    abs_errors = np.abs(errors)

    error_df = pd.DataFrame(
        {
            "date": test_df["date"],
            "modal_price": test_current,
            "actual_target_price": test_actual,
            "actual_price_change": test_df["price_change"],
            "predicted_price_change": test_pred_changes,
            "predicted_target_price": test_predicted_prices,
            "error": errors,
            "abs_error": abs_errors,
            "overprediction": np.maximum(0, errors),
            "underprediction": np.maximum(0, -errors),
        }
    )

    models_wheat_market_dir = PROCESSED_DATA_DIR / "models" / "wheat" / m_clean
    models_wheat_market_dir.mkdir(parents=True, exist_ok=True)
    error_analysis_path = models_wheat_market_dir / "error_analysis.csv"
    error_df.to_csv(error_analysis_path, index=False)
    print(f"Step 13 Complete: Saved error analysis to {error_analysis_path}")

    # ----------------------------------------------------
    # Step 14: Spike Analysis (Threshold from TRAIN)
    # ----------------------------------------------------
    train_abs_changes = np.abs(train_df["price_change"].values)
    spike_threshold = float(np.percentile(train_abs_changes, 90))

    test_abs_changes = np.abs(test_df["price_change"].values)
    is_spike = (test_abs_changes >= spike_threshold) | ((test_abs_changes / test_current) >= 0.10)
    is_normal = ~is_spike

    normal_mae = float(mean_absolute_error(test_actual[is_normal], test_predicted_prices[is_normal])) if is_normal.any() else test_mae
    spike_mae = float(mean_absolute_error(test_actual[is_spike], test_predicted_prices[is_spike])) if is_spike.any() else test_mae

    n_spikes = int(is_spike.sum())
    n_normal = int(is_normal.sum())

    print(f"Step 14 Complete: Spike Analysis (Threshold={spike_threshold:.2f} RS):")
    print(f"  Normal MAE ({n_normal} obs): {normal_mae:.2f} | Spike MAE ({n_spikes} obs): {spike_mae:.2f}")

    # ----------------------------------------------------
    # Step 15: Save Model Artifact & Model Registry
    # ----------------------------------------------------
    model_output_dir = get_model_dir(commodity="Wheat", model_type="change_xgboost_v3")
    model_output_dir.mkdir(parents=True, exist_ok=True)

    model_file_name = f"{m_clean}_final_model.json"
    feature_file_name = f"{m_clean}_final_features.csv"
    model_path = model_output_dir / model_file_name
    feature_path = model_output_dir / feature_file_name

    final_model.save_model(model_path)
    pd.DataFrame({"feature": selected_features}).to_csv(feature_path, index=False)

    register_model(
        commodity="Wheat",
        market=market,
        model_type="change_xgboost_v3",
        model_file=model_file_name,
        feature_file=feature_file_name,
        feature_count=len(selected_features),
        test_mae=round(test_mae, 2),
        status="VALIDATED",
        trained_at=datetime.now().strftime("%Y-%m-%d"),
        state=state,
        district=district,
        variety=sel_variety,
        grade=sel_grade,
        rmse=round(test_rmse, 2),
        r2=round(test_r2, 4),
        direction_accuracy=round(direction_acc, 1),
        baseline_mae=round(test_naive_mae, 2),
        improvement_pct=round(improvement_pct, 2),
        train_rows=len(train_df),
        val_rows=len(val_df),
        test_rows=len(test_df),
        model_path=str(model_path),
        feature_list=selected_features,
    )

    # Register in CommodityRegistry config
    cfg = get_commodity_config("Wheat")
    cfg.status = "VALIDATED"
    cfg.model_status = "VALIDATED"
    cfg.training_eligible = True
    cfg.model_count = max(cfg.model_count, 1)
    cfg.default_markets = list({*cfg.default_markets, market})
    cfg.historical_mae[m_clean] = float(round(test_mae, 2))
    cfg.notes = f"Genuine AGMARKNET historical model for {market}: MAE={round(test_mae, 2)}, R2={round(test_r2, 4)}"
    register_commodity_config(cfg)

    print(f"Step 15 Complete: Saved {market} model to {model_path} and registered in model_registry.json")

    # ----------------------------------------------------
    # Step 16-18: Inference & Recommendation Validation
    # ----------------------------------------------------
    predictor = ModelPredictor()
    latest_row = df_v3.iloc[[-1]]
    latest_price = float(latest_row["modal_price"].values[0])
    latest_date = pd.to_datetime(latest_row["date"].values[0])

    pred_res = predictor.predict_next_price(
        market=market,
        X_features=latest_row,
        current_price=latest_price,
        latest_date=latest_date,
        commodity="Wheat",
    )
    print(f"Step 17 Complete: ModelPredictor Inference OK (Current=Rs.{pred_res.current_price}, Predicted=Rs.{pred_res.predicted_price})")

    risk_engine = RiskEngine()
    risk_res = risk_engine.evaluate_risk_and_confidence(
        market=market,
        current_price=pred_res.current_price,
        predicted_change=pred_res.expected_change,
        recent_series=selected_df["modal_price"].tail(7),
        data_date=pred_res.date,
        commodity="Wheat",
    )
    print(f"Step 18 Complete: RiskEngine Evaluation OK (Level={risk_res.risk_level}, Score={risk_res.confidence_score}/100)")

    return {
        "commodity": "Wheat",
        "market": market,
        "state": state,
        "district": district,
        "raw_path": str(raw_path),
        "total_rows": total_rows,
        "unique_dates": unique_dates,
        "date_range": f"{start_date} to {end_date}",
        "variety": sel_variety,
        "grade": sel_grade,
        "quality_score": quality["quality_score"],
        "train_rows": len(train_df),
        "val_rows": len(val_df),
        "test_rows": len(test_df),
        "selected_features": selected_features,
        "best_n_features": best_n,
        "val_selection_results": val_selection_results,
        "naive_test_mae": round(test_naive_mae, 2),
        "test_mae": round(test_mae, 2),
        "test_rmse": round(test_rmse, 2),
        "test_r2": round(test_r2, 4),
        "test_mape": round(test_mape, 2),
        "direction_accuracy": round(direction_acc, 1),
        "improvement_pct": round(improvement_pct, 2),
        "normal_mae": round(normal_mae, 2),
        "spike_mae": round(spike_mae, 2),
        "n_spikes": n_spikes,
        "model_path": str(model_path),
        "status": "VALIDATED",
    }


def run_all_wheat_ml() -> Dict[str, Any]:
    print("=== STARTING TASK 4: REAL WHEAT ML PIPELINE (KHANNA & INDORE) ===")
    results = {}
    all_val_selection = []
    quality_summary = []

    for mkt_info in TARGET_MARKETS:
        res = profile_and_train_wheat_market(mkt_info)
        results[mkt_info["market"]] = res
        if "val_selection_results" in res:
            all_val_selection.extend(res["val_selection_results"])
        quality_summary.append({
            "market": mkt_info["market"],
            "state": mkt_info["state"],
            "status": res.get("status"),
            "quality_score": res.get("quality_score"),
            "train_rows": res.get("train_rows"),
            "val_rows": res.get("val_rows"),
            "test_rows": res.get("test_rows"),
            "test_mae": res.get("test_mae"),
            "baseline_mae": res.get("naive_test_mae"),
            "improvement_pct": res.get("improvement_pct"),
        })

    # Save feature selection summary
    models_wheat_dir = PROCESSED_DATA_DIR / "models" / "wheat"
    models_wheat_dir.mkdir(parents=True, exist_ok=True)
    if all_val_selection:
        pd.DataFrame(all_val_selection).to_csv(models_wheat_dir / "validation_feature_selection_results.csv", index=False)

    # Save quality report summary
    pd.DataFrame(quality_summary).to_csv(PROCESSED_DATA_DIR / "wheat_quality_report.csv", index=False)

    # Verify MandiRecommender for Wheat
    recommender = MandiRecommender()
    rec_res = recommender.recommend(
        farmer_latitude=30.7046,
        farmer_longitude=76.2166,
        quantity_quintals=10.0,
        commodity="Wheat",
    )
    print(f"\nStep 18 Complete: MandiRecommender Wheat OK (Top Mandi: {rec_res.recommended_mandi}, Evaluated={rec_res.total_mandis_evaluated})")

    return results


if __name__ == "__main__":
    res = run_all_wheat_ml()
    print("\nSUMMARY RESULT:")
    print(json.dumps(res, indent=2))
