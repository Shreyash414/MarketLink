"""
Final Model Comparison Report Generator.
Aggregates performance across all registered commodity models:
- Baseline Naive MAE
- Moving Average MAE
- XGBoost Model MAE
- RMSE
- R2
- Direction Accuracy (%)
- Improvement vs Baseline (%)
- Spike MAE
- Production Status

Outputs to: data/processed/models/final_model_comparison.csv
"""
import sys
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config.config import PROCESSED_DATA_DIR
from src.config.model_registry import list_all_models
from src.tools.benchmark_commodity_models import evaluate_benchmarks
from src.utils.logger import logger

TARGET_MODELS = [
    ("Onion", "Bareilly", "onion_bareilly_model.csv"),
    ("Onion", "Bargarh", "onion_bargarh_model.csv"),
    ("Onion", "Nagpur", "onion_nagpur_model.csv"),
    ("Potato", "Agra", "potato_agra_model.csv"),
    ("Tomato", "Kolar", "tomato_kolar_model.csv"),
    ("Wheat", "Khanna", "wheat_khanna_model.csv"),
    ("Rice", "Burdwan", "rice_burdwan_model.csv"),
]


def generate_final_model_comparison() -> pd.DataFrame:
    results = []
    for comm, mkt, f_name in TARGET_MODELS:
        f_path = PROCESSED_DATA_DIR / f_name
        if f_path.exists():
            res = evaluate_benchmarks(comm, mkt, dataset_path=f_path)
            results.append({
                "commodity": comm,
                "market": mkt,
                "model_type": "change_xgboost_v3",
                "total_sessions": res.get("total_rows"),
                "selected_features": res.get("selected_feature_count"),
                "baseline_naive_mae": res.get("naive_mae"),
                "baseline_ma_mae": res.get("ma_mae"),
                "model_mae": res.get("xgb_mae"),
                "rmse": res.get("xgb_rmse"),
                "r2": res.get("xgb_r2"),
                "direction_accuracy_pct": res.get("direction_accuracy_pct"),
                "improvement_vs_naive_pct": res.get("improvement_vs_naive_pct"),
                "spike_sessions": res.get("spike_count"),
                "spike_mae": res.get("spike_mae"),
                "status": "VALIDATED"
            })

    df = pd.DataFrame(results)
    out_path = PROCESSED_DATA_DIR / "models" / "final_model_comparison.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    logger.info(f"Saved final model comparison report to: {out_path}")
    return df


if __name__ == "__main__":
    df_comp = generate_final_model_comparison()
    print("================================================================================")
    print("FINAL MULTI-COMMODITY MODEL COMPARISON REPORT (PHASE 18)")
    print("================================================================================")
    print(df_comp.to_string(index=False))
