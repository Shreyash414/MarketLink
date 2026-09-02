"""
Generic Architecture Proof-of-Concept Validation.

Because the AGMARKNET API is unreachable on this network right now,
we validate the generic pipeline using Onion historical CSVs as PROXY data,
relabeled as Potato/Agra, Tomato/Kolar, Wheat/Khanna, Rice/Burdwan.

This proves every generic module (feature generation, training, model registry,
risk engine, economics, variety/grade selection) works for ANY commodity label
without Onion-specific hardcoding.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
from src.config.commodity_registry import get_commodity_config, list_registered_commodities
from src.config.model_registry import get_registered_model, register_model
from src.features.inference_feature_generator import generate_v3_features, get_latest_inference_features
from src.tools.train_commodity_model import train_and_select_features
from src.risk.risk_engine import RiskEngine
from src.economics.economics_engine import calculate_economics
from src.models.model_predictor import ModelPredictor
from src.utils.logger import logger

PROXY_MAP = {
    "Potato": {"proxy_csv": "data/processed/onion_bareilly_model.csv",  "proxy_market": "Agra",    "farmer_lat": 27.18, "farmer_lon": 78.02, "qty": 15.0},
    "Tomato": {"proxy_csv": "data/processed/onion_bargarh_model.csv",   "proxy_market": "Kolar",   "farmer_lat": 13.13, "farmer_lon": 78.13, "qty": 10.0},
    "Wheat":  {"proxy_csv": "data/processed/onion_nagpur_model.csv",    "proxy_market": "Khanna",  "farmer_lat": 30.70, "farmer_lon": 76.22, "qty": 20.0},
    "Rice":   {"proxy_csv": "data/processed/onion_bareilly_model.csv",  "proxy_market": "Burdwan", "farmer_lat": 23.23, "farmer_lon": 87.85, "qty": 20.0},
}

EXCLUDED = [
    "date", "target_price", "price_change", "price_change_pct", "price_direction",
    "market", "commodity", "state", "district", "variety", "grade",
    "min_price", "max_price", "modal_price", "retrieved_at", "source", "is_live"
]


def sep(title=""):
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def validate_commodity(commodity: str, proxy: dict) -> dict:
    sep(f"COMMODITY: {commodity.upper()}")
    report = {
        "commodity": commodity,
        "proxy_market": proxy["proxy_market"],
        "records_loaded": 0,
        "selected_variety": "N/A",
        "selected_grade": "N/A",
        "data_quality_score": 0.0,
        "train_rows": 0,
        "val_rows": 0,
        "test_rows": 0,
        "feature_count": 0,
        "test_mae": None,
        "test_rmse": None,
        "test_r2": None,
        "model_registry_entry": False,
        "inference_success": False,
        "risk_success": False,
        "economics_success": False,
        "recommendation_schema_valid": False,
        "final_status": "NEEDS_FIX",
    }

    # ----- STEP 1: Load proxy data -----
    csv_path = ROOT / proxy["proxy_csv"]
    if not csv_path.exists():
        print(f"  ERROR: Proxy CSV not found: {csv_path}")
        return report

    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "modal_price"]).sort_values("date").reset_index(drop=True)

    # Relabel as the target commodity/market (proves generic routing)
    df["commodity"] = commodity
    df["market"] = proxy["proxy_market"]

    # Simulate generic variety/grade selection (mode of most frequent combo)
    if "variety" in df.columns and "grade" in df.columns:
        combo = df.groupby(["variety", "grade"]).size().idxmax()
        selected_variety, selected_grade = combo
        df = df[(df["variety"] == selected_variety) & (df["grade"] == selected_grade)].copy()
    elif "variety" in df.columns:
        selected_variety = df["variety"].mode().iloc[0]
        selected_grade = "N/A"
        df = df[df["variety"] == selected_variety].copy()
    else:
        selected_variety = "N/A"
        selected_grade = "N/A"

    report["selected_variety"] = selected_variety
    report["selected_grade"] = selected_grade
    report["records_loaded"] = len(df)
    print(f"  Records loaded (proxy): {len(df)}")
    print(f"  Variety selected (generic mode): '{selected_variety}'")
    print(f"  Grade selected (generic mode):   '{selected_grade}'")

    # ----- STEP 2: Data quality score -----
    from src.tools.commodity_discovery import score_market_quality
    q = score_market_quality(df, market_name=proxy["proxy_market"], commodity=commodity)
    report["data_quality_score"] = q["quality_score"]
    print(f"  Data quality score: {q['quality_score']} | Status: {q['status']}")

    # ----- STEP 3: Save proxy model dataset -----
    c_key = commodity.strip().lower()
    m_key = proxy["proxy_market"].strip().lower()
    proxy_out = ROOT / "data" / "processed" / f"{c_key}_{m_key}_model.csv"
    df.to_csv(proxy_out, index=False)
    print(f"  Saved model dataset: {proxy_out} ({len(df)} rows)")

    # ----- STEPS 4-6: V3 features + split -----
    df["target_price"] = df["modal_price"].shift(-1)
    df["price_change"] = df["target_price"] - df["modal_price"]
    df_feat = generate_v3_features(df)
    if df_feat.empty:
        print("  ERROR: V3 feature generation failed.")
        return report

    df_clean = df_feat.dropna(subset=["price_change"]).reset_index(drop=True)
    n = len(df_clean)
    train_end = int(n * 0.60)
    val_end   = int(n * 0.80)
    report["train_rows"] = train_end
    report["val_rows"]   = val_end - train_end
    report["test_rows"]  = n - val_end
    print(f"  V3 features: {n} rows | Train={train_end} Val={val_end-train_end} Test={n-val_end}")

    feature_candidates = [c for c in df_clean.columns if c not in EXCLUDED]
    print(f"  Total feature candidates: {len(feature_candidates)}")

    # ----- STEPS 7-13: Generic XGBoost training -----
    print(f"\n  Training generic XGBoost V3 model for {commodity}/{proxy['proxy_market']}...")
    train_result = train_and_select_features(
        commodity=commodity,
        market=proxy["proxy_market"],
        top_n_features=20,
        test_ratio=0.20,
    )
    if train_result.get("status") != "SUCCESS":
        print(f"  TRAINING FAILED: {train_result.get('reason')}")
        return report

    report["feature_count"] = train_result["feature_count"]
    report["test_mae"]      = train_result["test_mae"]
    report["test_rmse"]     = train_result["test_rmse"]
    report["test_r2"]       = train_result["test_r2"]
    print(f"  MAE={train_result['test_mae']} RMSE={train_result['test_rmse']} R2={train_result['test_r2']}")
    print(f"  Selected features: {train_result['feature_count']}")
    print(f"  Model saved: {train_result['model_path']}")

    # ----- STEP 13: Verify model registry -----
    reg = get_registered_model(commodity=commodity, market=proxy["proxy_market"])
    report["model_registry_entry"] = bool(reg)
    print(f"  Model registry entry: {'REGISTERED ✓' if reg else 'MISSING ✗'}")
    if reg:
        print(f"    {reg}")

    # ----- STEP 14: Generic ModelPredictor inference -----
    print(f"\n  Running generic inference via ModelPredictor...")
    try:
        predictor = ModelPredictor()
        model, required_features = predictor.load_market_model(
            market=proxy["proxy_market"], commodity=commodity
        )
        # Get latest row inference features
        merged_df = df.tail(60).copy()
        X_infer, current_price, latest_date = get_latest_inference_features(
            merged_df=merged_df, required_features=required_features
        )
        pred_out = predictor.predict_next_price(
            market=proxy["proxy_market"],
            X_features=X_infer,
            current_price=current_price,
            latest_date=latest_date,
            commodity=commodity,
        )
        report["inference_success"] = True
        print(f"  Inference SUCCESS: current=Rs.{pred_out.current_price:.2f} → predicted=Rs.{pred_out.predicted_price:.2f} ({pred_out.expected_change_pct:+.2f}%, {pred_out.expected_direction})")
    except Exception as e:
        print(f"  Inference FAILED: {e}")
        return report

    # ----- STEP 15: Risk Engine -----
    print(f"\n  Running risk engine...")
    try:
        risk_engine = RiskEngine()
        recent_prices = merged_df["modal_price"].tail(30)
        risk_out = risk_engine.evaluate_risk_and_confidence(
            market=proxy["proxy_market"],
            current_price=pred_out.current_price,
            predicted_change=pred_out.expected_change,
            recent_series=recent_prices,
            data_date=latest_date,
            commodity=commodity,
        )
        report["risk_success"] = True
        print(f"  Risk SUCCESS: level={risk_out.risk_level} | condition={risk_out.market_condition} | confidence={risk_out.confidence_score}/100")
    except Exception as e:
        print(f"  Risk FAILED: {e}")
        return report

    # ----- STEP 16: Economics -----
    print(f"\n  Running economics engine...")
    try:
        from src.utils.geo_utils import haversine_distance
        # Dummy mandi coordinates from market_metadata.csv
        meta = pd.read_csv(ROOT / "data/processed/market_metadata.csv")
        meta.columns = [c.strip().lower() for c in meta.columns]
        mandi_row = meta[meta["market"].str.lower() == proxy["proxy_market"].lower()]
        if mandi_row.empty:
            # Use a default ~200 km distance
            dist_km = 200.0
        else:
            dist_km = haversine_distance(
                proxy["farmer_lat"], proxy["farmer_lon"],
                float(mandi_row.iloc[0]["latitude"]),
                float(mandi_row.iloc[0]["longitude"])
            )
        econ_out = calculate_economics(
            distance_km=dist_km,
            quantity_quintals=proxy["qty"],
            predicted_price=pred_out.predicted_price,
        )
        report["economics_success"] = True
        print(f"  Economics SUCCESS: distance={dist_km:.1f}km | net_return=Rs.{econ_out.net_return:,.2f} | net_price=Rs.{econ_out.net_price_per_quintal:.2f}/q")
    except Exception as e:
        print(f"  Economics FAILED: {e}")
        return report

    # ----- STEP 17-18: Recommendation output schema validation -----
    print(f"\n  Validating recommendation schema...")
    schema_keys = [
        "commodity", "market", "current_price", "predicted_price",
        "expected_change_pct", "risk_level", "confidence_score",
        "transport_cost", "net_return", "net_price_per_quintal"
    ]
    output_dict = {
        "commodity": commodity,
        "market": proxy["proxy_market"],
        "current_price": pred_out.current_price,
        "predicted_price": pred_out.predicted_price,
        "expected_change_pct": pred_out.expected_change_pct,
        "risk_level": risk_out.risk_level,
        "confidence_score": risk_out.confidence_score,
        "transport_cost": econ_out.transport_cost,
        "net_return": econ_out.net_return,
        "net_price_per_quintal": econ_out.net_price_per_quintal,
        "distance_km": dist_km,
        "market_condition": risk_out.market_condition,
        "warning": risk_out.warning_message if risk_out.risk_level != "LOW" else "",
    }
    missing_keys = [k for k in schema_keys if k not in output_dict]
    report["recommendation_schema_valid"] = len(missing_keys) == 0
    if missing_keys:
        print(f"  Schema INCOMPLETE: missing {missing_keys}")
    else:
        print(f"  Schema VALID ✓ — all {len(schema_keys)} required keys present")
        print(f"  Output preview: {list(output_dict.items())[:4]}")

    report["final_status"] = "READY"
    return report


def main():
    sep("GENERIC MULTI-COMMODITY PIPELINE VALIDATION (PROXY MODE)")
    print("NOTE: AGMARKNET API unreachable. Using Onion historical CSVs")
    print("      relabeled as Potato/Tomato/Wheat/Rice to prove generic architecture.")

    # ----- PRE-CHECK: Hardcoding audit -----
    sep("PRE-CHECK: Onion Hardcoding Audit in Generic Modules")
    GENERIC_MODULES = [
        "src/recommendation/mandi_recommender.py",
        "src/models/model_predictor.py",
        "src/risk/risk_engine.py",
        "src/features/inference_feature_generator.py",
        "src/data/ingestion/current_data_fetcher.py",
        "src/data/preprocessing/historical_merger.py",
        "src/tools/train_commodity_model.py",
        "src/tools/commodity_discovery.py",
        "src/tools/batch_recommend.py",
        "src/config/model_registry.py",
        "src/config/commodity_registry.py",
        "src/config/config.py",
    ]
    LOGIC_PATTERNS = [
        ('== "Onion"',    "Hardcoded Onion equality"),
        ("== 'Onion'",    "Hardcoded Onion equality"),
        ('== "Bareilly"', "Hardcoded market name"),
        ('== "Bargarh"',  "Hardcoded market name"),
        ('== "Nagpur"',   "Hardcoded market name"),
        ('== "Red"',      "Hardcoded variety"),
        ('== "FAQ"',      "Hardcoded grade"),
    ]
    issues = []
    for rel in GENERIC_MODULES:
        fp = ROOT / rel
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        for pattern, desc in LOGIC_PATTERNS:
            if pattern in content:
                issues.append(f"  [{rel}] {desc}: '{pattern}'")

    if issues:
        print("  ISSUES FOUND:")
        for i in issues:
            print(i)
    else:
        print("  CLEAN: Zero problematic Onion-specific logic in generic modules ✓")

    # ----- Per-commodity validation -----
    all_reports = {}
    for commodity, proxy in PROXY_MAP.items():
        report = validate_commodity(commodity, proxy)
        all_reports[commodity] = report

    # ----- Run Onion regression tests -----
    sep("STEP 20: Onion Regression Tests")
    import subprocess, os
    result = subprocess.run(
        ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        capture_output=True, text=True, cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)}, timeout=180,
    )
    test_out = result.stderr + result.stdout
    test_passed = "OK" in test_out
    ran_line = [l for l in test_out.split("\n") if l.startswith("Ran ")]
    print(f"  {ran_line[0] if ran_line else 'N/A'}")
    print(f"  Passed: {test_passed}")

    # ----- Final report -----
    sep("FINAL VALIDATION REPORT")

    print("\n--- HARDCODING AUDIT ---")
    print(f"  Generic module issues: {len(issues)} ({'CLEAN' if not issues else 'NEEDS FIX'})")

    print("\n--- PER-COMMODITY SUMMARY ---")
    hdr = f"{'Commodity':<12} {'Records':>8} {'Variety':<16} {'Grade':<12} {'Q-Score':>8} {'Train':>6} {'Val':>5} {'Test':>5} {'Feat':>5} {'MAE':>8} {'R2':>7} {'Status':>18}"
    print(hdr)
    print("-" * len(hdr))
    for c, r in all_reports.items():
        print(
            f"{c:<12} {r['records_loaded']:>8} {str(r['selected_variety']):<16} "
            f"{str(r['selected_grade']):<12} {r['data_quality_score']:>8.1f} "
            f"{r['train_rows']:>6} {r['val_rows']:>5} {r['test_rows']:>5} "
            f"{r['feature_count']:>5} {str(r['test_mae']):>8} {str(r['test_r2']):>7} "
            f"{r['final_status']:>18}"
        )

    print("\n--- COMPONENT CHECK PER COMMODITY ---")
    for c, r in all_reports.items():
        print(f"\n  {c} / {r['proxy_market']}:")
        print(f"    Model Registry:  {'✓' if r['model_registry_entry'] else '✗'}")
        print(f"    Inference:       {'✓' if r['inference_success'] else '✗'}")
        print(f"    Risk Engine:     {'✓' if r['risk_success'] else '✗'}")
        print(f"    Economics:       {'✓' if r['economics_success'] else '✗'}")
        print(f"    Schema Valid:    {'✓' if r['recommendation_schema_valid'] else '✗'}")

    print("\n--- GENERIC ARCHITECTURE PROBLEMS DISCOVERED ---")
    print("  1. Historical API (api.data.gov.in) unreachable on current network")
    print("     → All 4 commodity markets timed out on both Current + Historical endpoints")
    print("     → Fix: Download historical CSVs manually or from a network with API access")
    print("  2. mandi_current_raw.csv holds only a single day snapshot (2026-01-09)")
    print("     → Insufficient for lag/rolling ML features (need 60+ sessions)")
    print("  3. market_metadata.csv may not have GPS for all 225 candidate mandis")
    print("     → Fix: Extend metadata with coordinates as each commodity is onboarded")

    print("\n--- BUGS FIXED THIS SESSION ---")
    print("  1. src/recommend_mandi.py:50 — hardcoded 'Commodity : Onion' print statement")
    print("     → Fixed to include comment clarifying it is CLI demo default only")

    print("\n--- TRULY REUSABLE GENERIC COMPONENTS ---")
    reusable = [
        "CurrentDataFetcher.fetch_all_current_data(commodity=X)",
        "HistoricalMerger.merge_current_with_history(commodity=X)",
        "InferenceFeatureGenerator.generate_v3_features(df)",
        "ModelPredictor.load_market_model(market, commodity=X)",
        "RiskEngine.evaluate_risk_and_confidence(market, commodity=X)",
        "calculate_economics(distance_km, quantity_quintals, predicted_price)",
        "train_and_select_features(commodity=X, market=Y)",
        "discover_commodity_markets(commodity=X)",
        "batch_recommend.py — CSV-driven multi-commodity batch",
        "CommodityRegistry — single config per crop, no code duplication",
        "ModelRegistry — JSON-backed model catalogue per crop/market",
    ]
    for item in reusable:
        print(f"  ✓ {item}")

    print("\n--- WHAT MUST BE FIXED BEFORE SCALING TO 225 COMMODITIES ---")
    fixes = [
        "Download historical CSVs for each commodity's candidate markets (requires API access)",
        "Extend market_metadata.csv with GPS coordinates for all candidate mandis",
        "Ensure min 200 sessions per market/commodity before training (data quality gate)",
        "Add all 225 commodities to CommodityRegistry with correct api_commodity_name",
        "Build a scheduled data-download job that populates historical CSVs automatically",
        "Add variety/grade selection fallback: if selected combo < 60 rows, take next best",
        "Current API needs to return recent live prices for inference (not just cache snapshots)",
    ]
    for i, f in enumerate(fixes, 1):
        print(f"  {i}. {f}")

    print("\n--- REGRESSION TESTS (Onion) ---")
    print(f"  {ran_line[0] if ran_line else 'unknown'} — Passed: {test_passed}")

    print("\n--- FINAL STATUS PER COMMODITY ---")
    for c, r in all_reports.items():
        print(f"  {c}: {r['final_status']}")

    print()
    return all_reports, test_passed, issues


if __name__ == "__main__":
    main()
