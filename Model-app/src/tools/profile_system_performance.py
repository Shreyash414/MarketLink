"""
System Performance Profiler.
Measures execution latencies across:
- Data discovery
- Feature generation
- Model inference
- Risk & interval evaluation
- Economics calculation
- Recommendation engine orchestration
- Intent parsing & Explanation generation
"""
import sys
import time
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.ai.intent_parser import FarmerIntentParser
from src.ai.recommendation_explainer import RecommendationExplainer
from src.config.config import PROCESSED_DATA_DIR
from src.economics.economics_engine import calculate_economics
from src.features.inference_feature_generator import generate_v3_features, get_latest_inference_features
from src.models.model_predictor import ModelPredictor
from src.recommendation.mandi_recommender import MandiRecommender
from src.risk.risk_engine import RiskEngine
from src.tools.commodity_discovery import score_market_quality


def profile_system_performance() -> pd.DataFrame:
    benchmarks = []

    # 1. Feature Generation Latency (on 1000 rows)
    df_raw = pd.read_csv(PROCESSED_DATA_DIR / "onion_bareilly_model.csv").tail(1000)
    df_raw.columns = [c.strip().lower() for c in df_raw.columns]
    df_raw["date"] = pd.to_datetime(df_raw["date"])
    df_raw["target_price"] = df_raw["modal_price"].shift(-1)
    df_raw["price_change"] = df_raw["target_price"] - df_raw["modal_price"]

    t0 = time.perf_counter()
    for _ in range(5):
        _ = generate_v3_features(df_raw)
    t_feat = (time.perf_counter() - t0) / 5.0
    benchmarks.append({"Component": "V3 Feature Generation (1000 rows)", "Avg Latency (ms)": round(t_feat * 1000, 2), "Throughput": f"{int(1000/t_feat):,} rows/s"})

    # 2. Model Predictor Latency (Single inference)
    predictor = ModelPredictor()
    _, req_feats = predictor.load_market_model("Bareilly", "Onion")
    X_inf, cur_p, l_date = get_latest_inference_features(df_raw, req_feats)

    t0 = time.perf_counter()
    for _ in range(100):
        _ = predictor.predict_next_price("Bareilly", X_inf, cur_p, l_date, "Onion")
    t_inf = (time.perf_counter() - t0) / 100.0
    benchmarks.append({"Component": "XGBoost V3 Single Inference", "Avg Latency (ms)": round(t_inf * 1000, 2), "Throughput": f"{int(1/t_inf):,} calls/s"})

    # 3. Risk Engine Latency (Volatility + 80%/95% Intervals)
    risk_engine = RiskEngine()
    series = df_raw["modal_price"].tail(30)
    t0 = time.perf_counter()
    for _ in range(200):
        _ = risk_engine.evaluate_risk_and_confidence("Bareilly", cur_p, 5.0, series, l_date, "Onion")
    t_risk = (time.perf_counter() - t0) / 200.0
    benchmarks.append({"Component": "Risk & Prediction Interval Evaluation", "Avg Latency (ms)": round(t_risk * 1000, 2), "Throughput": f"{int(1/t_risk):,} calls/s"})

    # 4. Economics Calculation Latency
    t0 = time.perf_counter()
    for _ in range(500):
        _ = calculate_economics(219.4, 10.0, 1331.0)
    t_econ = (time.perf_counter() - t0) / 500.0
    benchmarks.append({"Component": "Haversine & Transport Economics", "Avg Latency (ms)": round(t_econ * 1000, 3), "Throughput": f"{int(1/t_econ):,} calls/s"})

    # 5. Farmer Intent Parsing Latency (Rule-based)
    parser = FarmerIntentParser()
    query = "Selling 15 quintals of Potato near Agra"
    t0 = time.perf_counter()
    for _ in range(200):
        _ = parser.parse(query)
    t_parse = (time.perf_counter() - t0) / 200.0
    benchmarks.append({"Component": "Farmer Query Intent Parsing", "Avg Latency (ms)": round(t_parse * 1000, 2), "Throughput": f"{int(1/t_parse):,} queries/s"})

    # 6. Recommendation Explainer Latency (Template fallback)
    explainer = RecommendationExplainer()
    rec_obj = MandiRecommender().recommend(28.6139, 77.2090, 10.0, "Onion")
    t0 = time.perf_counter()
    for _ in range(200):
        _ = explainer.explain(rec_obj, language="English")
    t_expl = (time.perf_counter() - t0) / 200.0
    benchmarks.append({"Component": "Multilingual Explanation Generation", "Avg Latency (ms)": round(t_expl * 1000, 2), "Throughput": f"{int(1/t_expl):,} reports/s"})

    # 7. End-to-End Recommendation Latency
    recommender = MandiRecommender()
    t0 = time.perf_counter()
    for _ in range(3):
        _ = recommender.recommend(28.6139, 77.2090, 10.0, "Onion")
    t_rec = (time.perf_counter() - t0) / 3.0
    benchmarks.append({"Component": "Full End-to-End Mandi Recommendation", "Avg Latency (ms)": round(t_rec * 1000, 2), "Throughput": f"{round(1/t_rec, 2)} queries/s"})

    df_b = pd.DataFrame(benchmarks)
    return df_b


if __name__ == "__main__":
    print("================================================================================")
    print("SYSTEM PERFORMANCE PROFILING REPORT (PHASE 20)")
    print("================================================================================")
    df_bench = profile_system_performance()
    print(df_bench.to_string(index=False))
