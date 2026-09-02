import pandas as pd
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

INPUT_DIR = Path(
    "data/processed/models/change_xgboost_v3"
)

OUTPUT_DIR = Path(
    "data/processed/models/change_xgboost_v3/feature_selection"
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
# HOW MANY TOP FEATURES TO TEST
# ============================================================

TOP_K_VALUES = [
    10,
    20,
    30,
    40,
    50
]


# ============================================================
# PROCESS EACH MARKET
# ============================================================

for market in markets:

    print("\n")
    print("=" * 70)
    print(
        f"FEATURE SELECTION: {market.upper()}"
    )
    print("=" * 70)

    importance_file = (
        INPUT_DIR /
        f"{market}_feature_importance.csv"
    )

    if not importance_file.exists():

        raise FileNotFoundError(
            f"Feature importance file not found:\n"
            f"{importance_file}"
        )

    importance = pd.read_csv(
        importance_file
    )

    # Sort strongest → weakest
    importance = importance.sort_values(
        "importance",
        ascending=False
    ).reset_index(drop=True)

    print(
        f"\nTotal available features: "
        f"{len(importance)}"
    )

    # ========================================================
    # CREATE TOP-K FEATURE FILES
    # ========================================================

    for k in TOP_K_VALUES:

        selected = importance.head(k)

        output_file = (
            OUTPUT_DIR /
            f"{market}_top_{k}_features.csv"
        )

        selected.to_csv(
            output_file,
            index=False
        )

        print(
            f"Top {k} features saved → "
            f"{output_file}"
        )

    # ========================================================
    # DISPLAY TOP 20
    # ========================================================

    print("\nTop 20 features:")
    print("-" * 70)

    print(
        importance.head(20)
        .to_string(index=False)
    )


print("\n")
print("=" * 70)
print("FEATURE SELECTION FILES CREATED")
print("=" * 70)