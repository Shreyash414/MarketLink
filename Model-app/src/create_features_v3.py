import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

INPUT_DIR = Path("data/processed/features")
OUTPUT_DIR = Path("data/processed/features_v3")

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
# PROCESS EACH MARKET
# ============================================================

all_data = []

for market in markets:

    print("\n")
    print("=" * 70)
    print(f"CREATING V3 FEATURES: {market.upper()}")
    print("=" * 70)

    input_file = (
        INPUT_DIR /
        f"{market}_features.csv"
    )

    if not input_file.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_file}"
        )

    df = pd.read_csv(input_file)

    print(
        f"Original rows: {len(df)}"
    )

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df = df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    price = df["modal_price"]

    # ========================================================
    # 1. ABSOLUTE PRICE CHANGE
    # ========================================================

    df["price_change_abs_1"] = (
        df["price_change_1"].abs()
    )

    df["price_change_abs_7"] = (
        df["price_change_7"].abs()
    )

    # ========================================================
    # 2. SHORT-TERM MOMENTUM
    # ========================================================

    df["momentum_3"] = (
        price - price.shift(3)
    )

    df["momentum_7"] = (
        price - price.shift(7)
    )

    df["momentum_14"] = (
        price - price.shift(14)
    )

    df["momentum_30"] = (
        price - price.shift(30)
    )

    # Percentage momentum

    df["momentum_pct_3"] = (
        df["momentum_3"]
        / price.shift(3).replace(0, np.nan)
        * 100
    )

    df["momentum_pct_7"] = (
        df["momentum_7"]
        / price.shift(7).replace(0, np.nan)
        * 100
    )

    df["momentum_pct_14"] = (
        df["momentum_14"]
        / price.shift(14).replace(0, np.nan)
        * 100
    )

    # ========================================================
    # 3. SHORT-TERM VOLATILITY
    # ========================================================

    df["price_volatility_3"] = (
        price.shift(1)
        .rolling(3)
        .std()
    )

    df["price_volatility_7"] = (
        price.shift(1)
        .rolling(7)
        .std()
    )

    df["price_volatility_14"] = (
        price.shift(1)
        .rolling(14)
        .std()
    )

    df["price_volatility_30"] = (
        price.shift(1)
        .rolling(30)
        .std()
    )

    # ========================================================
    # 4. RECENT HIGH / LOW
    # ========================================================

    df["recent_max_7"] = (
        price.shift(1)
        .rolling(7)
        .max()
    )

    df["recent_min_7"] = (
        price.shift(1)
        .rolling(7)
        .min()
    )

    df["recent_max_14"] = (
        price.shift(1)
        .rolling(14)
        .max()
    )

    df["recent_min_14"] = (
        price.shift(1)
        .rolling(14)
        .min()
    )

    df["recent_max_30"] = (
        price.shift(1)
        .rolling(30)
        .max()
    )

    df["recent_min_30"] = (
        price.shift(1)
        .rolling(30)
        .min()
    )

    # ========================================================
    # 5. DISTANCE FROM RECENT HIGH / LOW
    # ========================================================

    df["distance_from_high_7"] = (
        price - df["recent_max_7"]
    )

    df["distance_from_low_7"] = (
        price - df["recent_min_7"]
    )

    df["distance_from_high_14"] = (
        price - df["recent_max_14"]
    )

    df["distance_from_low_14"] = (
        price - df["recent_min_14"]
    )

    # ========================================================
    # 6. RECENT PRICE RANGE
    # ========================================================

    df["price_range_7"] = (
        df["recent_max_7"]
        - df["recent_min_7"]
    )

    df["price_range_14"] = (
        df["recent_max_14"]
        - df["recent_min_14"]
    )

    df["price_range_30"] = (
        df["recent_max_30"]
        - df["recent_min_30"]
    )

    # ========================================================
    # 7. RANGE AS PERCENTAGE OF CURRENT PRICE
    # ========================================================

    df["price_range_pct_7"] = (
        df["price_range_7"]
        / price.replace(0, np.nan)
        * 100
    )

    df["price_range_pct_14"] = (
        df["price_range_14"]
        / price.replace(0, np.nan)
        * 100
    )

    df["price_range_pct_30"] = (
        df["price_range_30"]
        / price.replace(0, np.nan)
        * 100
    )

    # ========================================================
    # 8. VOLATILITY REGIME
    # ========================================================

    df["volatility_ratio_7_30"] = (
        df["price_volatility_7"]
        / df["price_volatility_30"].replace(
            0,
            np.nan
        )
    )

    # ========================================================
    # 9. TREND STRENGTH
    # ========================================================

    df["trend_strength_7"] = (
        df["momentum_7"]
        / df["price_volatility_7"].replace(
            0,
            np.nan
        )
    )

    df["trend_strength_14"] = (
        df["momentum_14"]
        / df["price_volatility_14"].replace(
            0,
            np.nan
        )
    )

    # ========================================================
    # 10. PRICE POSITION INSIDE RECENT RANGE
    # ========================================================

    range_7 = (
        df["recent_max_7"]
        - df["recent_min_7"]
    )

    range_14 = (
        df["recent_max_14"]
        - df["recent_min_14"]
    )

    df["price_position_7"] = (
        (price - df["recent_min_7"])
        / range_7.replace(0, np.nan)
    )

    df["price_position_14"] = (
        (price - df["recent_min_14"])
        / range_14.replace(0, np.nan)
    )

    # ========================================================
    # REMOVE INF / NAN
    # ========================================================

    df = df.replace(
        [np.inf, -np.inf],
        np.nan
    )

    before_drop = len(df)

    df = df.dropna().reset_index(
        drop=True
    )

    removed = (
        before_drop - len(df)
    )

    print(
        f"Rows removed because of "
        f"feature warm-up: {removed}"
    )

    # ========================================================
    # FEATURE COUNT
    # ========================================================

    excluded = [
        "date",
        "target_price",
        "price_change",
        "price_change_pct",
        "price_direction"
    ]

    feature_columns = [
        col
        for col in df.columns
        if col not in excluded
    ]

    print(
        f"Final rows: {len(df)}"
    )

    print(
        f"Total features: {len(feature_columns)}"
    )

    print("\nNew V3 features:")

    original_features = set(
        pd.read_csv(input_file, nrows=1).columns
    )

    new_features = [
        col
        for col in df.columns
        if col not in original_features
    ]

    for feature in new_features:
        print(
            f"  - {feature}"
        )

    # ========================================================
    # SAVE MARKET DATA
    # ========================================================

    output_file = (
        OUTPUT_DIR /
        f"{market}_features_v3.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nSaved: {output_file}"
    )

    all_data.append(df)


# ============================================================
# COMBINED DATASET
# ============================================================

combined = pd.concat(
    all_data,
    ignore_index=True
)

combined_file = (
    OUTPUT_DIR /
    "onion_all_markets_features_v3.csv"
)

combined.to_csv(
    combined_file,
    index=False
)

print("\n")
print("=" * 70)
print("V3 FEATURE ENGINEERING COMPLETE")
print("=" * 70)

print(
    f"Combined rows: {len(combined)}"
)

print(
    f"Combined features: "
    f"{len(combined.columns)} columns"
)

print(
    f"\nSaved: {combined_file}"
)