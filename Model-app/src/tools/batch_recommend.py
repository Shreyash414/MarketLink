"""
Batch Mandi Recommendation Interface.
Processes multiple farmer requests across commodities in batch and generates consolidated outputs.
"""
import argparse
from pathlib import Path
from typing import List, Optional

import pandas as pd

from src.recommendation.mandi_recommender import recommend_mandi
from src.utils.logger import logger


def run_batch_recommendations(
    input_file: Path,
    output_file: Optional[Path] = None,
    transport_rate: float = 3.0
) -> pd.DataFrame:
    """
    Process a batch CSV file containing columns: commodity, latitude, longitude, quantity_quintals.
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input batch file not found: {input_path}")

    df_requests = pd.read_csv(input_path)
    df_requests.columns = [c.strip().lower() for c in df_requests.columns]

    required_cols = ["commodity", "latitude", "longitude", "quantity_quintals"]
    missing = [c for c in required_cols if c not in df_requests.columns]
    if missing:
        raise KeyError(f"Batch file missing required columns: {missing}")

    logger.info(f"Loaded batch file with {len(df_requests)} farmer requests.")

    results_summary = []

    for idx, row in df_requests.iterrows():
        commodity = str(row["commodity"]).strip()
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        qty = float(row["quantity_quintals"])

        logger.info(f"Processing request #{idx + 1}: {commodity} ({qty}q) at ({lat}, {lon})")

        try:
            rec_result = recommend_mandi(
                farmer_latitude=lat,
                farmer_longitude=lon,
                quantity_quintals=qty,
                commodity=commodity,
                transport_rate=transport_rate
            )

            if rec_result.recommendations:
                top = rec_result.recommendations[0]
                results_summary.append({
                    "request_id": idx + 1,
                    "commodity": commodity,
                    "farmer_lat": lat,
                    "farmer_lon": lon,
                    "quantity_quintals": qty,
                    "status": "RECOMMENDED",
                    "top_mandi": top.mandi,
                    "state": top.state,
                    "distance_km": top.distance_km,
                    "current_price": top.current_price,
                    "predicted_price": top.predicted_price,
                    "transport_cost": top.transport_cost,
                    "net_return": top.net_return,
                    "net_price_per_quintal": top.net_price_per_quintal,
                    "risk_level": top.risk_level,
                    "confidence_score": top.confidence_score,
                    "reason": top.reason
                })
            else:
                results_summary.append({
                    "request_id": idx + 1,
                    "commodity": commodity,
                    "farmer_lat": lat,
                    "farmer_lon": lon,
                    "quantity_quintals": qty,
                    "status": "NO_RECOMMENDATION",
                    "top_mandi": "NONE",
                    "state": "N/A",
                    "distance_km": 0.0,
                    "current_price": 0.0,
                    "predicted_price": 0.0,
                    "transport_cost": 0.0,
                    "net_return": 0.0,
                    "net_price_per_quintal": 0.0,
                    "risk_level": "N/A",
                    "confidence_score": 0.0,
                    "reason": f"No eligible mandis or trained models found for {commodity}."
                })

        except Exception as e:
            logger.error(f"Error processing request #{idx + 1} for {commodity}: {e}")
            results_summary.append({
                "request_id": idx + 1,
                "commodity": commodity,
                "farmer_lat": lat,
                "farmer_lon": lon,
                "quantity_quintals": qty,
                "status": "ERROR",
                "top_mandi": "NONE",
                "state": "N/A",
                "distance_km": 0.0,
                "current_price": 0.0,
                "predicted_price": 0.0,
                "transport_cost": 0.0,
                "net_return": 0.0,
                "net_price_per_quintal": 0.0,
                "risk_level": "N/A",
                "confidence_score": 0.0,
                "reason": str(e)
            })

    df_out = pd.DataFrame(results_summary)

    if output_file:
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(out_p, index=False)
        logger.info(f"Saved batch recommendations to {out_p}")

    return df_out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run batch mandi recommendations from CSV.")
    parser.add_argument("--input", type=str, default="data/sample_batch_requests.csv", help="Path to input CSV")
    parser.add_argument("--output", type=str, default="data/processed/recommendation/batch_results.csv", help="Path to output CSV")
    args = parser.parse_args()

    # Create sample batch if not present
    sample_file = Path(args.input)
    if not sample_file.exists():
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([
            {"commodity": "Onion", "latitude": 28.6139, "longitude": 77.2090, "quantity_quintals": 10.0},
            {"commodity": "Onion", "latitude": 21.1458, "longitude": 79.0882, "quantity_quintals": 25.0},
            {"commodity": "Potato", "latitude": 27.1767, "longitude": 78.0081, "quantity_quintals": 15.0},
            {"commodity": "Tomato", "latitude": 13.1367, "longitude": 78.1291, "quantity_quintals": 8.0},
            {"commodity": "Wheat", "latitude": 30.7071, "longitude": 76.2168, "quantity_quintals": 50.0},
            {"commodity": "Rice", "latitude": 23.2324, "longitude": 87.8615, "quantity_quintals": 30.0},
        ]).to_csv(sample_file, index=False)
        print(f"Created sample batch file at {sample_file}")

    results = run_batch_recommendations(input_file=sample_file, output_file=Path(args.output))
    print("\n" + "=" * 80)
    print("BATCH RECOMMENDATION SUMMARY RESULTS")
    print("=" * 80)
    print(results[["request_id", "commodity", "status", "top_mandi", "distance_km", "net_return", "risk_level", "confidence_score"]].to_string(index=False))
    print("=" * 80)
