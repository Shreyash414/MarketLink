import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

INPUT_DIR = Path(
    "data/processed/models/change_xgboost_v2"
)

OUTPUT_DIR = Path(
    "data/processed/models/change_xgboost_v2/error_analysis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# MARKETS
# ============================================================

markets = [
    "bareilly",
    "bargarh",
    "nagpur"
]


# ============================================================
# ANALYZE EACH MARKET
# ============================================================

all_results = []


for market in markets:

    print("\n")
    print("=" * 80)
    print(f"ERROR ANALYSIS: {market.upper()}")
    print("=" * 80)


    # ========================================================
    # LOAD PREDICTIONS
    # ========================================================

    file_path = (
        INPUT_DIR /
        f"{market}_test_predictions.csv"
    )

    if not file_path.exists():

        print(
            f"Prediction file not found: {file_path}"
        )

        continue


    df = pd.read_csv(file_path)


    print("\nColumns:")
    print(df.columns.tolist())


    # ========================================================
    # DISPLAY FIRST ROWS
    # ========================================================

    print("\nFirst 5 predictions:")
    print(
        df.head().to_string(index=False)
    )


    # ========================================================
    # CONVERT DATE
    # ========================================================

    if "date" in df.columns:

        df["date"] = pd.to_datetime(
            df["date"]
        )

    elif "Arrival_Date" in df.columns:

        df["Arrival_Date"] = pd.to_datetime(
            df["Arrival_Date"]
        )

        df["date"] = df["Arrival_Date"]

    else:

        raise ValueError(
            f"No date column found for {market}"
        )


    # ========================================================
    # FIND PRICE COLUMNS
    # ========================================================

    actual_candidates = [
        "actual_next_price",
        "actual_price",
        "target_price",
        "next_price"
    ]

    predicted_candidates = [
        "predicted_next_price",
        "predicted_price",
        "prediction"
    ]


    actual_col = None

    for col in actual_candidates:

        if col in df.columns:

            actual_col = col
            break


    predicted_col = None

    for col in predicted_candidates:

        if col in df.columns:

            predicted_col = col
            break


    if actual_col is None:

        raise ValueError(
            f"Could not find actual price column "
            f"for {market}."
        )


    if predicted_col is None:

        raise ValueError(
            f"Could not find predicted price column "
            f"for {market}."
        )


    print(
        f"\nActual price column: {actual_col}"
    )

    print(
        f"Predicted price column: {predicted_col}"
    )


    # ========================================================
    # CLEAN
    # ========================================================

    df = df[
        [
            "date",
            actual_col,
            predicted_col
        ]
    ].copy()


    df = df.dropna()


    df = df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )


    # ========================================================
    # STANDARD COLUMN NAMES
    # ========================================================

    df.rename(
        columns={
            actual_col: "actual_price",
            predicted_col: "predicted_price"
        },
        inplace=True
    )


    # ========================================================
    # ERROR CALCULATION
    # ========================================================

    df["error"] = (
        df["predicted_price"]
        - df["actual_price"]
    )


    df["absolute_error"] = (
        df["error"]
        .abs()
    )


    df["percentage_error"] = (
        df["absolute_error"]
        / df["actual_price"].replace(0, np.nan)
        * 100
    )


    # ========================================================
    # PRICE CHANGE
    # ========================================================

    df["actual_change"] = (
        df["actual_price"]
        - df["actual_price"].shift(1)
    )


    df["actual_change_pct"] = (
        df["actual_change"]
        / df["actual_price"].shift(1).replace(
            0,
            np.nan
        )
        * 100
    )


    # ========================================================
    # BASIC METRICS
    # ========================================================

    mae = df["absolute_error"].mean()

    rmse = np.sqrt(
        np.mean(
            df["error"] ** 2
        )
    )


    print("\nBasic Error Metrics")
    print("-" * 50)

    print(
        f"MAE  : ₹{mae:.2f}"
    )

    print(
        f"RMSE : ₹{rmse:.2f}"
    )


    # ========================================================
    # LARGEST ERRORS
    # ========================================================

    largest_errors = (
        df.sort_values(
            "absolute_error",
            ascending=False
        )
        .head(20)
    )


    print("\nTop 20 Largest Prediction Errors")
    print("-" * 50)

    print(
        largest_errors[
            [
                "date",
                "actual_price",
                "predicted_price",
                "error",
                "absolute_error"
            ]
        ].to_string(index=False)
    )


    # ========================================================
    # SPIKE ANALYSIS
    # ========================================================

    # Define a major movement as an absolute
    # price movement greater than 10%.

    spike_mask = (
        df["actual_change_pct"]
        .abs()
        >= 10
    )


    spike_rows = df[
        spike_mask
    ].copy()


    normal_rows = df[
        ~spike_mask
    ].copy()


    print("\nSpike Analysis")
    print("-" * 50)

    print(
        f"Spike observations : "
        f"{len(spike_rows)}"
    )

    print(
        f"Normal observations: "
        f"{len(normal_rows)}"
    )


    if len(spike_rows) > 0:

        spike_mae = (
            spike_rows["absolute_error"]
            .mean()
        )

        print(
            f"Spike MAE : ₹{spike_mae:.2f}"
        )

    else:

        spike_mae = np.nan


    if len(normal_rows) > 0:

        normal_mae = (
            normal_rows["absolute_error"]
            .mean()
        )

        print(
            f"Normal MAE: ₹{normal_mae:.2f}"
        )

    else:

        normal_mae = np.nan


    # ========================================================
    # SAVE ERROR DATA
    # ========================================================

    error_file = (
        OUTPUT_DIR /
        f"{market}_error_analysis.csv"
    )


    df.to_csv(
        error_file,
        index=False
    )


    # ========================================================
    # SAVE TOP ERRORS
    # ========================================================

    top_error_file = (
        OUTPUT_DIR /
        f"{market}_largest_errors.csv"
    )


    largest_errors.to_csv(
        top_error_file,
        index=False
    )


    # ========================================================
    # PLOT 1
    # ACTUAL VS PREDICTED
    # ========================================================

    plt.figure(
        figsize=(14, 6)
    )

    plt.plot(
        df["date"],
        df["actual_price"],
        label="Actual Price"
    )

    plt.plot(
        df["date"],
        df["predicted_price"],
        label="Predicted Price"
    )

    plt.xlabel(
        "Date"
    )

    plt.ylabel(
        "Price (₹/quintal)"
    )

    plt.title(
        f"{market.title()} - Actual vs Predicted Price"
    )

    plt.legend()

    plt.grid(
        alpha=0.3
    )

    plt.tight_layout()


    plot_file = (
        OUTPUT_DIR /
        f"{market}_actual_vs_predicted.png"
    )


    plt.savefig(
        plot_file,
        dpi=200
    )

    plt.close()


    # ========================================================
    # PLOT 2
    # PREDICTION ERROR OVER TIME
    # ========================================================

    plt.figure(
        figsize=(14, 6)
    )

    plt.plot(
        df["date"],
        df["error"]
    )

    plt.axhline(
        0,
        linestyle="--"
    )

    plt.xlabel(
        "Date"
    )

    plt.ylabel(
        "Prediction Error (₹)"
    )

    plt.title(
        f"{market.title()} - Prediction Error Over Time"
    )

    plt.grid(
        alpha=0.3
    )

    plt.tight_layout()


    error_plot_file = (
        OUTPUT_DIR /
        f"{market}_error_over_time.png"
    )


    plt.savefig(
        error_plot_file,
        dpi=200
    )

    plt.close()


    # ========================================================
    # PLOT 3
    # ACTUAL VS PREDICTED SCATTER
    # ========================================================

    plt.figure(
        figsize=(8, 8)
    )

    plt.scatter(
        df["actual_price"],
        df["predicted_price"],
        alpha=0.5
    )


    min_price = min(
        df["actual_price"].min(),
        df["predicted_price"].min()
    )

    max_price = max(
        df["actual_price"].max(),
        df["predicted_price"].max()
    )


    plt.plot(
        [min_price, max_price],
        [min_price, max_price],
        linestyle="--"
    )


    plt.xlabel(
        "Actual Price (₹/quintal)"
    )

    plt.ylabel(
        "Predicted Price (₹/quintal)"
    )

    plt.title(
        f"{market.title()} - Actual vs Predicted"
    )

    plt.grid(
        alpha=0.3
    )

    plt.tight_layout()


    scatter_file = (
        OUTPUT_DIR /
        f"{market}_actual_vs_predicted_scatter.png"
    )


    plt.savefig(
        scatter_file,
        dpi=200
    )

    plt.close()


    # ========================================================
    # STORE SUMMARY
    # ========================================================

    all_results.append({

        "market": market,

        "test_rows": len(df),

        "mae": mae,

        "rmse": rmse,

        "spike_rows": len(spike_rows),

        "spike_mae": spike_mae,

        "normal_mae": normal_mae
    })


# ============================================================
# FINAL SUMMARY
# ============================================================

summary = pd.DataFrame(
    all_results
)


summary_file = (
    OUTPUT_DIR /
    "error_analysis_summary.csv"
)


summary.to_csv(
    summary_file,
    index=False
)


print("\n")
print("=" * 80)
print("ERROR ANALYSIS COMPLETE")
print("=" * 80)


print("\nSummary:")

if len(summary) > 0:

    print(
        summary.to_string(
            index=False
        )
    )


print("\nFiles saved in:")

print(
    OUTPUT_DIR
)