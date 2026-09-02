import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE = Path("data/processed")

SPIKE_DIR = BASE / "spike_analysis"

V3_PREDICTION_DIR = (
    BASE
    / "models"
    / "change_xgboost_v3"
)

OUTPUT_DIR = (
    BASE
    / "spike_analysis"
    / "v3_error_analysis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


MARKETS = [
    "bareilly",
    "bargarh",
    "nagpur"
]


# ============================================================
# FIND V3 PREDICTION FILE
# ============================================================

def find_prediction_file(market):

    possible_files = [
        V3_PREDICTION_DIR / f"{market}_predictions.csv",
        V3_PREDICTION_DIR / f"{market}_test_predictions.csv",
        V3_PREDICTION_DIR / "final" / f"{market}_predictions.csv",
        V3_PREDICTION_DIR / "final" / f"{market}_test_predictions.csv",
    ]

    for path in possible_files:

        if path.exists():
            return path

    return None


# ============================================================
# FIND COLUMN
# ============================================================

def find_column(df, possible_names):

    for name in possible_names:

        if name in df.columns:
            return name

    return None


# ============================================================
# ANALYZE MARKET
# ============================================================

def analyze_market(market):

    print()
    print("=" * 60)
    print(market.upper())
    print("=" * 60)

    # --------------------------------------------------------
    # Spike file
    # --------------------------------------------------------

    spike_path = (
        SPIKE_DIR
        / f"{market}_spikes.csv"
    )

    if not spike_path.exists():

        print(
            f"Spike file not found: {spike_path}"
        )

        return None

    # --------------------------------------------------------
    # Prediction file
    # --------------------------------------------------------

    prediction_path = find_prediction_file(
        market
    )

    if prediction_path is None:

        print(
            f"V3 prediction file not found for {market}"
        )

        print(
            f"Expected location under:"
            f"\n{V3_PREDICTION_DIR}"
        )

        return None

    print(
        f"Spike file      : {spike_path}"
    )

    print(
        f"Prediction file : {prediction_path}"
    )

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    spike_df = pd.read_csv(
        spike_path
    )

    pred_df = pd.read_csv(
        prediction_path
    )

    print(
        f"Spike columns:"
        f"\n{spike_df.columns.tolist()}"
    )

    print(
        f"Prediction columns:"
        f"\n{pred_df.columns.tolist()}"
    )

    # --------------------------------------------------------
    # Date columns
    # --------------------------------------------------------

    spike_date_col = find_column(
        spike_df,
        [
            "date",
            "Date",
            "Arrival_Date",
            "arrival_date"
        ]
    )

    pred_date_col = find_column(
        pred_df,
        [
            "date",
            "Date",
            "Arrival_Date",
            "arrival_date"
        ]
    )

    if spike_date_col is None:

        raise ValueError(
            "No date column found in spike data."
        )

    if pred_date_col is None:

        raise ValueError(
            "No date column found in V3 predictions."
        )

    # --------------------------------------------------------
    # Convert dates
    # --------------------------------------------------------

    spike_df[spike_date_col] = pd.to_datetime(
        spike_df[spike_date_col],
        errors="coerce"
    )

    pred_df[pred_date_col] = pd.to_datetime(
        pred_df[pred_date_col],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Find actual and predicted price
    # --------------------------------------------------------

    actual_col = find_column(
        pred_df,
        [
            "target_price",
            "actual_price",
            "actual",
            "next_price"
        ]
    )

    predicted_col = find_column(
        pred_df,
        [
            "predicted_price",
            "prediction",
            "predicted"
        ]
    )

    if actual_col is None:

        raise ValueError(
            "Could not find actual price column "
            "in V3 predictions."
        )

    if predicted_col is None:

        raise ValueError(
            "Could not find predicted price column "
            "in V3 predictions."
        )

    print(
        f"Actual price column    : {actual_col}"
    )

    print(
        f"Predicted price column : {predicted_col}"
    )

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    pred_df[actual_col] = pd.to_numeric(
        pred_df[actual_col],
        errors="coerce"
    )

    pred_df[predicted_col] = pd.to_numeric(
        pred_df[predicted_col],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Calculate prediction error
    # --------------------------------------------------------

    pred_df["absolute_error"] = (
        pred_df[actual_col]
        - pred_df[predicted_col]
    ).abs()

    pred_df["squared_error"] = (
        pred_df[actual_col]
        - pred_df[predicted_col]
    ) ** 2

    # --------------------------------------------------------
    # Prepare spike data
    # --------------------------------------------------------

    spike_merge = spike_df[
        [
            spike_date_col,
            "is_spike",
            "spike_type",
            "price_change_pct",
            "spike_threshold_pct"
        ]
    ].copy()

    # Rename date for easier merging

    spike_merge = spike_merge.rename(
        columns={
            spike_date_col: "date"
        }
    )

    pred_df = pred_df.rename(
        columns={
            pred_date_col: "date"
        }
    )

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    merged = pd.merge(
        pred_df,
        spike_merge,
        on="date",
        how="inner"
    )

    print()
    print(
        f"V3 prediction rows : {len(pred_df)}"
    )

    print(
        f"Matched rows        : {len(merged)}"
    )

    # --------------------------------------------------------
    # Remove invalid rows
    # --------------------------------------------------------

    merged = merged.dropna(
        subset=[
            "absolute_error",
            "is_spike"
        ]
    ).copy()

    merged["is_spike"] = merged[
        "is_spike"
    ].astype(int)

    # ========================================================
    # NORMAL / SPIKE SPLIT
    # ========================================================

    normal = merged[
        merged["is_spike"] == 0
    ]

    spikes = merged[
        merged["is_spike"] == 1
    ]

    # --------------------------------------------------------
    # MAE
    # --------------------------------------------------------

    normal_mae = (
        normal["absolute_error"].mean()
        if len(normal) > 0
        else np.nan
    )

    spike_mae = (
        spikes["absolute_error"].mean()
        if len(spikes) > 0
        else np.nan
    )

    # --------------------------------------------------------
    # RMSE
    # --------------------------------------------------------

    normal_rmse = (
        np.sqrt(
            normal["squared_error"].mean()
        )
        if len(normal) > 0
        else np.nan
    )

    spike_rmse = (
        np.sqrt(
            spikes["squared_error"].mean()
        )
        if len(spikes) > 0
        else np.nan
    )

    # --------------------------------------------------------
    # Error ratio
    # --------------------------------------------------------

    if normal_mae > 0:

        spike_error_ratio = (
            spike_mae / normal_mae
        )

    else:

        spike_error_ratio = np.nan

    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print()
    print("NORMAL CONDITIONS")
    print(
        f"Observations : {len(normal)}"
    )
    print(
        f"MAE          : ₹{normal_mae:.2f}"
    )
    print(
        f"RMSE         : ₹{normal_rmse:.2f}"
    )

    print()
    print("SPIKE CONDITIONS")
    print(
        f"Observations : {len(spikes)}"
    )
    print(
        f"MAE          : ₹{spike_mae:.2f}"
    )
    print(
        f"RMSE         : ₹{spike_rmse:.2f}"
    )

    print()
    print(
        f"Spike / Normal MAE ratio : "
        f"{spike_error_ratio:.2f}x"
    )

    # ========================================================
    # SAVE DETAILED DATA
    # ========================================================

    detailed_path = (
        OUTPUT_DIR
        / f"{market}_spike_vs_error.csv"
    )

    merged.to_csv(
        detailed_path,
        index=False
    )

    print(
        f"\nDetailed results saved:"
        f"\n{detailed_path}"
    )

    # ========================================================
    # RETURN SUMMARY
    # ========================================================

    return {
        "market": market,
        "matched_observations": len(merged),
        "normal_observations": len(normal),
        "spike_observations": len(spikes),
        "normal_mae": normal_mae,
        "normal_rmse": normal_rmse,
        "spike_mae": spike_mae,
        "spike_rmse": spike_rmse,
        "spike_normal_mae_ratio": spike_error_ratio
    }


# ============================================================
# MAIN
# ============================================================

results = []

for market in MARKETS:

    try:

        result = analyze_market(
            market
        )

        if result is not None:

            results.append(result)

    except Exception as e:

        print()
        print(
            f"ERROR processing {market}:"
        )
        print(e)


# ============================================================
# SAVE SUMMARY
# ============================================================

if results:

    summary = pd.DataFrame(
        results
    )

    summary_path = (
        OUTPUT_DIR
        / "spike_vs_error_summary.csv"
    )

    summary.to_csv(
        summary_path,
        index=False
    )

    print()
    print("=" * 60)
    print("FINAL SPIKE VS V3 ERROR SUMMARY")
    print("=" * 60)

    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print(
        f"Summary saved to:"
        f"\n{summary_path}"
    )

else:

    print(
        "\nNo results generated."
    )