import os
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

PROCESSED_DIR = "data/processed"

OUTPUT_DIR = "data/processed/features"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


DATASETS = {
    "Bareilly": "onion_bareilly_model.csv",
    "Bargarh": "onion_bargarh_model.csv",
    "Nagpur": "onion_nagpur_model.csv"
}


# ============================================================
# LOAD DATA
# ============================================================

def load_data(market, filename):

    path = os.path.join(
        PROCESSED_DIR,
        filename
    )

    print("\n" + "=" * 80)
    print(f"LOADING {market}")
    print("=" * 80)

    df = pd.read_csv(path)

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df = df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    print(
        "Rows:",
        len(df)
    )

    print(
        "Date:",
        df["date"].min().date(),
        "→",
        df["date"].max().date()
    )

    return df


# ============================================================
# TIME FEATURES
# ============================================================

def create_time_features(df):

    print(
        "\nCreating time features..."
    )

    df["year"] = (
        df["date"].dt.year
    )

    df["month"] = (
        df["date"].dt.month
    )

    df["quarter"] = (
        df["date"].dt.quarter
    )

    df["day_of_week"] = (
        df["date"].dt.dayofweek
    )

    # Day of year captures annual position

    df["day_of_year"] = (
        df["date"].dt.dayofyear
    )

    # Cyclic encoding
    #
    # December and January are close to each other
    # mathematically after this transformation.

    df["month_sin"] = (
        np.sin(
            2 * np.pi * df["month"] / 12
        )
    )

    df["month_cos"] = (
        np.cos(
            2 * np.pi * df["month"] / 12
        )
    )

    df["day_of_year_sin"] = (
        np.sin(
            2 * np.pi *
            df["day_of_year"] / 365.25
        )
    )

    df["day_of_year_cos"] = (
        np.cos(
            2 * np.pi *
            df["day_of_year"] / 365.25
        )
    )

    return df


# ============================================================
# LAG FEATURES
# ============================================================

def create_lag_features(df):

    print(
        "Creating lag features..."
    )

    price = df["modal_price"]

    # Previous observed market sessions

    df["lag_1"] = (
        price.shift(1)
    )

    df["lag_2"] = (
        price.shift(2)
    )

    df["lag_3"] = (
        price.shift(3)
    )

    df["lag_7"] = (
        price.shift(7)
    )

    df["lag_14"] = (
        price.shift(14)
    )

    df["lag_30"] = (
        price.shift(30)
    )

    return df


# ============================================================
# ROLLING FEATURES
# ============================================================

def create_rolling_features(df):

    print(
        "Creating rolling features..."
    )

    price = df["modal_price"]

    # shift(1) is critical.
    #
    # It prevents today's price from being used
    # to calculate today's feature.
    #
    # Otherwise we would leak the target information.

    previous_price = price.shift(1)

    df["rolling_mean_3"] = (
        previous_price
        .rolling(3)
        .mean()
    )

    df["rolling_mean_7"] = (
        previous_price
        .rolling(7)
        .mean()
    )

    df["rolling_mean_14"] = (
        previous_price
        .rolling(14)
        .mean()
    )

    df["rolling_mean_30"] = (
        previous_price
        .rolling(30)
        .mean()
    )

    df["rolling_std_7"] = (
        previous_price
        .rolling(7)
        .std()
    )

    df["rolling_std_14"] = (
        previous_price
        .rolling(14)
        .std()
    )

    df["rolling_std_30"] = (
        previous_price
        .rolling(30)
        .std()
    )

    return df


# ============================================================
# MOMENTUM FEATURES
# ============================================================

def create_momentum_features(df):

    print(
        "Creating momentum features..."
    )

    price = df["modal_price"]

    # Previous observation price changes

    df["price_change_1"] = (
        price.shift(1)
        -
        price.shift(2)
    )

    df["price_change_7"] = (
        price.shift(1)
        -
        price.shift(8)
    )

    # Percentage changes

    previous_1 = price.shift(2)

    previous_7 = price.shift(8)

    df["price_change_pct_1"] = (
        (
            price.shift(1)
            -
            previous_1
        )
        /
        previous_1
    ) * 100

    df["price_change_pct_7"] = (
        (
            price.shift(1)
            -
            previous_7
        )
        /
        previous_7
    ) * 100

    return df


# ============================================================
# TARGET
# ============================================================

def create_target(df):

    print(
        "Creating target..."
    )

    # Predict the NEXT observed market price.

    df["target_price"] = (
        df["modal_price"]
        .shift(-1)
    )

    return df


# ============================================================
# REMOVE UNNECESSARY COLUMNS
# ============================================================

def select_model_columns(df):

    columns = [

        # Identification
        "date",
        "market",
        "commodity",
        "variety",
        "grade",

        # Current observed price
        "modal_price",

        # Historical prices
        "lag_1",
        "lag_2",
        "lag_3",
        "lag_7",
        "lag_14",
        "lag_30",

        # Rolling statistics
        "rolling_mean_3",
        "rolling_mean_7",
        "rolling_mean_14",
        "rolling_mean_30",

        "rolling_std_7",
        "rolling_std_14",
        "rolling_std_30",

        # Time
        "year",
        "month",
        "quarter",
        "day_of_week",
        "day_of_year",

        # Cyclic time
        "month_sin",
        "month_cos",
        "day_of_year_sin",
        "day_of_year_cos",

        # Momentum
        "price_change_1",
        "price_change_7",
        "price_change_pct_1",
        "price_change_pct_7",

        # Target
        "target_price"
    ]

    return df[columns]


# ============================================================
# REMOVE NaN CREATED BY LAGS
# ============================================================

def remove_nan_rows(df):

    before = len(df)

    df = df.dropna().copy()

    removed = (
        before - len(df)
    )

    print(
        "Rows removed because of "
        f"lag/rolling/target NaN: {removed}"
    )

    return df


# ============================================================
# VALIDATE FEATURES
# ============================================================

def validate_features(df, market):

    print("\n" + "-" * 80)
    print(
        f"FEATURE VALIDATION — {market}"
    )
    print("-" * 80)

    print(
        "Rows:",
        len(df)
    )

    print(
        "Columns:",
        len(df.columns)
    )

    print(
        "\nMissing values:"
    )

    print(
        df.isna()
        .sum()
        .to_string()
    )

    print(
        "\nDuplicate dates:",
        df["date"].duplicated().sum()
    )

    print(
        "\nFeature columns:"
    )

    for column in df.columns:

        print(
            f"  {column}"
        )


# ============================================================
# PROCESS ONE MARKET
# ============================================================

def process_market(
    market,
    filename
):

    df = load_data(
        market,
        filename
    )

    # Time
    df = create_time_features(
        df
    )

    # Historical prices
    df = create_lag_features(
        df
    )

    # Rolling statistics
    df = create_rolling_features(
        df
    )

    # Momentum
    df = create_momentum_features(
        df
    )

    # Future target
    df = create_target(
        df
    )

    # Select final features
    df = select_model_columns(
        df
    )

    # Remove rows where features
    # cannot be calculated

    df = remove_nan_rows(
        df
    )

    # Validate
    validate_features(
        df,
        market
    )

    # Save
    output_path = os.path.join(
        OUTPUT_DIR,
        f"{market.lower()}_features.csv"
    )

    df.to_csv(
        output_path,
        index=False
    )

    print(
        "\nSaved:",
        output_path
    )

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 80)
    print("ONION PRICE FEATURE ENGINEERING")
    print("=" * 80)

    all_data = []

    for market, filename in DATASETS.items():

        df = process_market(
            market,
            filename
        )

        all_data.append(
            df
        )

    # ========================================================
    # COMBINED DATASET
    # ========================================================

    print("\n")
    print("=" * 80)
    print("CREATING COMBINED FEATURE DATASET")
    print("=" * 80)

    combined = pd.concat(
        all_data,
        ignore_index=True
    )

    combined = combined.sort_values(
        [
            "market",
            "date"
        ]
    ).reset_index(
        drop=True
    )

    combined_path = os.path.join(
        OUTPUT_DIR,
        "onion_all_markets_features.csv"
    )

    combined.to_csv(
        combined_path,
        index=False
    )

    print(
        "Combined rows:",
        len(combined)
    )

    print(
        "Saved:",
        combined_path
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n")
    print("=" * 80)
    print("FEATURE ENGINEERING COMPLETE")
    print("=" * 80)

    print(
        "\nOutput directory:"
    )

    print(
        OUTPUT_DIR
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()