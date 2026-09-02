"""
CLI validation script for Task 8: Real-Time Data Freshness & Inference Reliability Layer.
Evaluates all 8 genuine target commodity/market configurations and reports full metadata.
"""
from src.recommendation.mandi_recommender import MandiRecommender, recommend_mandi
from src.models.model_quality_gate import get_model_quality_metadata
from src.data.data_reliability import evaluate_data_reliability
from src.data.preprocessing.historical_merger import merge_current_with_history
from src.data.ingestion.current_data_fetcher import CurrentDataFetcher
from src.config.commodity_registry import get_commodity_config

COMMODITY_MANDI_PAIRS = [
    ("Onion", "Bareilly", 28.6139, 77.2090),
    ("Onion", "Bargarh", 28.6139, 77.2090),
    ("Onion", "Nagpur", 28.6139, 77.2090),
    ("Potato", "Agra", 27.1767, 78.0081),
    ("Tomato", "Kolar", 13.1367, 78.1292),
    ("Wheat", "Khanna", 30.7046, 76.2166),
    ("Wheat", "Indore", 22.7196, 75.8577),
    ("Rice", "Burdwan", 23.2324, 87.8615),
]

def main():
    print("=" * 110)
    print(f"{'COMMODITY':<10} | {'MANDI':<10} | {'PRED STATUS':<15} | {'MODEL STATUS':<20} | {'RELIABILITY':<11} | {'SRC':<6} | {'FRESHNESS':<13} | {'SESSIONS':<8} | {'REASON / WARNING'}")
    print("=" * 110)

    for comm, mandi, lat, lon in COMMODITY_MANDI_PAIRS:
        # Run recommendation
        res = recommend_mandi(
            farmer_latitude=lat,
            farmer_longitude=lon,
            quantity_quintals=10.0,
            commodity=comm,
            farmer_facing=True
        )

        model_meta = get_model_quality_metadata(commodity=comm, market=mandi)
        m_status = model_meta["usage_status"]
        m_score = f"{model_meta['reliability_score']:.1f}/100"

        # Find matching item if evaluated
        matched_item = next((item for item in res.recommendations if item.mandi.lower() == mandi.lower()), None)

        if matched_item:
            pred_status = "ALLOWED"
            data_src = matched_item.data_source
            freshness = matched_item.data_freshness_status
            sessions = matched_item.historical_session_count
            reason_warn = matched_item.warning if matched_item.warning else "Normal operation"
        else:
            pred_status = "BLOCKED"
            data_src = res.data_source if res.data_source != "NONE" else "CACHE"
            freshness = "N/A"
            sessions = 0
            reason_warn = f"Model {m_status}" if m_status in ("DISABLED", "RESEARCH_ONLY") else "Blocked by safety gate"

        print(f"{comm:<10} | {mandi:<10} | {pred_status:<15} | {m_status:<20} | {m_score:<11} | {data_src:<6} | {freshness:<13} | {sessions:<8} | {reason_warn}")

    print("=" * 110)

if __name__ == "__main__":
    main()
