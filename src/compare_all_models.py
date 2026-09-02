import pandas as pd
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASELINE_FILE = Path(
    "data/processed/models/baseline_results.csv"
)

DIRECT_XGB_FILE = Path(
    "data/processed/models/xgboost/xgboost_results.csv"
)

TUNED_XGB_FILE = Path(
    "data/processed/models/xgboost_tuning/tuned_xgboost_results.csv"
)

CHANGE_XGB_FILE = Path(
    "data/processed/models/change_xgboost_v2/"
    "change_xgboost_v2_results.csv"
)

OUTPUT_DIR = Path(
    "data/processed/models/final_comparison"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD RESULT FILES
# ============================================================

print("=" * 70)
print("LOADING MODEL RESULTS")
print("=" * 70)


baseline = pd.read_csv(BASELINE_FILE)
direct = pd.read_csv(DIRECT_XGB_FILE)
tuned = pd.read_csv(TUNED_XGB_FILE)
change = pd.read_csv(CHANGE_XGB_FILE)


print("\nBaseline columns:")
print(baseline.columns.tolist())

print("\nDirect XGBoost columns:")
print(direct.columns.tolist())

print("\nTuned XGBoost columns:")
print(tuned.columns.tolist())

print("\nChange XGBoost V2 columns:")
print(change.columns.tolist())


# ============================================================
# HELPER: GET MARKET ROW
# ============================================================

def get_market_rows(df, market):
    """
    Return all rows belonging to a particular market.
    """

    if "market" not in df.columns:
        raise ValueError(
            f"'market' column not found.\n"
            f"Available columns: {df.columns.tolist()}"
        )

    rows = df[
        df["market"]
        .astype(str)
        .str.lower()
        .str.strip()
        == market.lower()
    ]

    if len(rows) == 0:
        raise ValueError(
            f"Market '{market}' not found in dataframe."
        )

    return rows


# ============================================================
# GET BASELINE TEST RESULT
# ============================================================

def get_naive_baseline(df, market):

    market_rows = get_market_rows(
        df,
        market
    )

    # Your baseline CSV uses:
    #
    # market | dataset | model | MAE | RMSE | MAPE
    #

    if "dataset" not in df.columns:
        raise ValueError(
            "Baseline file does not contain 'dataset' column."
        )

    if "model" not in df.columns:
        raise ValueError(
            "Baseline file does not contain 'model' column."
        )

    test_rows = market_rows[
        market_rows["dataset"]
        .astype(str)
        .str.lower()
        .str.strip()
        == "test"
    ]

    if len(test_rows) == 0:
        raise ValueError(
            f"No TEST baseline result found for {market}."
        )

    naive_rows = test_rows[
        test_rows["model"]
        .astype(str)
        .str.lower()
        .str.strip()
        .str.contains("naive")
    ]

    if len(naive_rows) == 0:

        print("\nAvailable baseline rows for", market)
        print(test_rows.to_string(index=False))

        raise ValueError(
            f"Naive baseline not found for {market}."
        )

    return naive_rows.iloc[0]


# ============================================================
# GET MODEL ROW
# ============================================================

def get_model_row(df, market):

    rows = get_market_rows(
        df,
        market
    )

    # All our XGBoost result files contain
    # one row per market.
    return rows.iloc[0]


# ============================================================
# MAIN MARKETS
# ============================================================

markets = [
    "bareilly",
    "bargarh",
    "nagpur"
]


# ============================================================
# BUILD FINAL COMPARISON
# ============================================================

results = []


for market in markets:

    print("\n")
    print("-" * 70)
    print(market.upper())
    print("-" * 70)


    # ========================================================
    # NAIVE BASELINE
    # ========================================================

    naive_row = get_naive_baseline(
        baseline,
        market
    )

    naive_mae = float(
        naive_row["MAE"]
    )

    naive_rmse = float(
        naive_row["RMSE"]
    )


    # ========================================================
    # DIRECT XGBOOST
    # ========================================================

    direct_row = get_model_row(
        direct,
        market
    )

    direct_mae = float(
        direct_row["test_mae"]
    )

    direct_rmse = float(
        direct_row["test_rmse"]
    )

    direct_r2 = float(
        direct_row["test_r2"]
    )


    # ========================================================
    # TUNED XGBOOST
    # ========================================================

    tuned_row = get_model_row(
        tuned,
        market
    )

    tuned_mae = float(
        tuned_row["test_mae"]
    )

    tuned_rmse = float(
        tuned_row["test_rmse"]
    )

    tuned_r2 = float(
        tuned_row["test_r2"]
    )


    # ========================================================
    # PRICE-CHANGE XGBOOST V2
    # ========================================================

    change_row = get_model_row(
        change,
        market
    )

    change_mae = float(
        change_row["test_price_mae"]
    )

    change_rmse = float(
        change_row["test_price_rmse"]
    )

    change_r2 = float(
        change_row["test_price_r2"]
    )

    direction_accuracy = float(
        change_row["direction_accuracy"]
    )


    # ========================================================
    # IMPROVEMENTS
    # ========================================================

    # Improvement of Change XGBoost V2
    # compared with Naive baseline.

    improvement_vs_naive = (
        (naive_mae - change_mae)
        / naive_mae
        * 100
    )


    # Improvement compared with
    # Direct XGBoost.

    improvement_vs_direct = (
        (direct_mae - change_mae)
        / direct_mae
        * 100
    )


    # Improvement compared with
    # Tuned Direct XGBoost.

    improvement_vs_tuned = (
        (tuned_mae - change_mae)
        / tuned_mae
        * 100
    )


    # ========================================================
    # BEST MODEL
    # ========================================================

    model_scores = {
        "Naive": naive_mae,
        "Direct XGBoost": direct_mae,
        "Tuned XGBoost": tuned_mae,
        "Change XGBoost V2": change_mae
    }

    best_model = min(
        model_scores,
        key=model_scores.get
    )

    best_mae = model_scores[
        best_model
    ]


    # ========================================================
    # STORE RESULT
    # ========================================================

    results.append({

        "market": market,

        # -------------------------------
        # Naive
        # -------------------------------

        "naive_mae": naive_mae,
        "naive_rmse": naive_rmse,

        # -------------------------------
        # Direct XGBoost
        # -------------------------------

        "direct_xgb_mae": direct_mae,
        "direct_xgb_rmse": direct_rmse,
        "direct_xgb_r2": direct_r2,

        # -------------------------------
        # Tuned XGBoost
        # -------------------------------

        "tuned_xgb_mae": tuned_mae,
        "tuned_xgb_rmse": tuned_rmse,
        "tuned_xgb_r2": tuned_r2,

        # -------------------------------
        # Change XGBoost V2
        # -------------------------------

        "change_xgb_v2_mae": change_mae,
        "change_xgb_v2_rmse": change_rmse,
        "change_xgb_v2_r2": change_r2,

        "direction_accuracy":
            direction_accuracy,

        # -------------------------------
        # Improvements
        # -------------------------------

        "improvement_vs_naive_percent":
            improvement_vs_naive,

        "improvement_vs_direct_xgb_percent":
            improvement_vs_direct,

        "improvement_vs_tuned_xgb_percent":
            improvement_vs_tuned,

        # -------------------------------
        # Best model
        # -------------------------------

        "best_model":
            best_model,

        "best_mae":
            best_mae
    })


# ============================================================
# CREATE DATAFRAME
# ============================================================

comparison = pd.DataFrame(
    results
)


# ============================================================
# ROUND NUMBERS
# ============================================================

numeric_columns = comparison.select_dtypes(
    include=["float64", "float32", "int64", "int32"]
).columns

comparison[numeric_columns] = comparison[
    numeric_columns
].round(4)


# ============================================================
# DISPLAY MAIN COMPARISON
# ============================================================

print("\n")
print("=" * 100)
print("FINAL MODEL COMPARISON")
print("=" * 100)


display_columns = [

    "market",

    "naive_mae",

    "direct_xgb_mae",

    "tuned_xgb_mae",

    "change_xgb_v2_mae",

    "change_xgb_v2_r2",

    "direction_accuracy",

    "improvement_vs_naive_percent",

    "improvement_vs_tuned_xgb_percent",

    "best_model"
]


print(
    comparison[
        display_columns
    ].to_string(
        index=False
    )
)


# ============================================================
# DETAILED RESULTS
# ============================================================

print("\n")
print("=" * 100)
print("DETAILED TEST RESULTS")
print("=" * 100)


for _, row in comparison.iterrows():

    print("\n")
    print(
        f"MARKET: {row['market'].upper()}"
    )

    print("-" * 60)

    print(
        f"Naive Baseline:"
    )

    print(
        f"  MAE  : ₹{row['naive_mae']:.2f}"
    )

    print(
        f"  RMSE : ₹{row['naive_rmse']:.2f}"
    )


    print(
        f"\nDirect XGBoost:"
    )

    print(
        f"  MAE  : ₹{row['direct_xgb_mae']:.2f}"
    )

    print(
        f"  RMSE : ₹{row['direct_xgb_rmse']:.2f}"
    )

    print(
        f"  R²   : {row['direct_xgb_r2']:.4f}"
    )


    print(
        f"\nTuned XGBoost:"
    )

    print(
        f"  MAE  : ₹{row['tuned_xgb_mae']:.2f}"
    )

    print(
        f"  RMSE : ₹{row['tuned_xgb_rmse']:.2f}"
    )

    print(
        f"  R²   : {row['tuned_xgb_r2']:.4f}"
    )


    print(
        f"\nChange XGBoost V2:"
    )

    print(
        f"  MAE  : ₹{row['change_xgb_v2_mae']:.2f}"
    )

    print(
        f"  RMSE : ₹{row['change_xgb_v2_rmse']:.2f}"
    )

    print(
        f"  R²   : {row['change_xgb_v2_r2']:.4f}"
    )

    print(
        f"  Direction Accuracy : "
        f"{row['direction_accuracy']:.2f}%"
    )


    print(
        f"\nImprovement of Change XGBoost V2:"
    )

    print(
        f"  vs Naive       : "
        f"{row['improvement_vs_naive_percent']:.2f}%"
    )

    print(
        f"  vs Direct XGB  : "
        f"{row['improvement_vs_direct_xgb_percent']:.2f}%"
    )

    print(
        f"  vs Tuned XGB   : "
        f"{row['improvement_vs_tuned_xgb_percent']:.2f}%"
    )


    print(
        f"\nBEST MODEL:"
    )

    print(
        f"  {row['best_model']}"
    )

    print(
        f"  MAE = ₹{row['best_mae']:.2f}"
    )


# ============================================================
# SAVE FULL COMPARISON
# ============================================================

output_file = (
    OUTPUT_DIR /
    "all_model_comparison.csv"
)

comparison.to_csv(
    output_file,
    index=False
)


# ============================================================
# SAVE A SMALL SIH SUMMARY
# ============================================================

sih_summary = comparison[
    [
        "market",
        "naive_mae",
        "tuned_xgb_mae",
        "change_xgb_v2_mae",
        "change_xgb_v2_r2",
        "improvement_vs_naive_percent",
        "best_model"
    ]
].copy()


sih_summary_file = (
    OUTPUT_DIR /
    "sih_model_summary.csv"
)

sih_summary.to_csv(
    sih_summary_file,
    index=False
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("BEST MODEL PER MARKET")
print("=" * 70)


for _, row in comparison.iterrows():

    print(
        f"{row['market'].upper():10} -> "
        f"{row['best_model']:20} "
        f"MAE = ₹{row['best_mae']:.2f}"
    )


print("\n")
print("=" * 70)
print("FILES SAVED")
print("=" * 70)

print(
    f"\nFull comparison:"
)

print(
    output_file
)

print(
    f"\nSIH summary:"
)

print(
    sih_summary_file
)


print("\n")
print("=" * 70)
print("COMPARISON COMPLETE")
print("=" * 70)