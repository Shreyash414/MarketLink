import os
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

MARKETS = [
    "bareilly",
    "bargarh",
    "nagpur"
]

INPUT_DIR = "data/processed/features"

OUTPUT_DIR = "data/processed/change_features_v2"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# CREATE DATASET FOR ONE MARKET
# ============================================================

def create_change_dataset(market):

    print("\n" + "=" * 70)
    print(f"CREATING CHANGE FEATURES V2: {market.upper()}")
    print("=" * 70)

    input_path = os.path.join(
        INPUT_DIR,
        f"{market}_features.csv"
    )

    df = pd.read_csv(input_path)

    print(f"Input rows: {len(df)}")

    # --------------------------------------------------------
    # Convert date
    # --------------------------------------------------------

    df["date"] = pd.to_datetime(
        df["date"]
    )

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    df = df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # create_features.py already created:
    #
    # target_price
    #
    # which is the next observed price.
    #
    # We will NOT use target_price as a feature.
    # --------------------------------------------------------

    # Create price-change target

    df["price_change"] = (
        df["target_price"]
        - df["modal_price"]
    )

    # --------------------------------------------------------
    # Percentage change
    # --------------------------------------------------------

    df["price_change_pct"] = np.where(
        df["modal_price"] != 0,
        (
            df["price_change"]
            / df["modal_price"]
        ) * 100,
        np.nan
    )

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    df["price_direction"] = np.where(
        df["price_change"] > 0,
        "up",
        np.where(
            df["price_change"] < 0,
            "down",
            "same"
        )
    )

    # --------------------------------------------------------
    # Remove invalid target rows
    # --------------------------------------------------------

    before = len(df)

    df = df.dropna(
        subset=[
            "modal_price",
            "target_price",
            "price_change"
        ]
    ).copy()

    removed = before - len(df)

    print(
        f"Rows removed: {removed}"
    )

    # --------------------------------------------------------
    # Check columns
    # --------------------------------------------------------

    print("\nAvailable columns:")

    for column in df.columns:

        print(
            f"  - {column}"
        )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    print("\nPrice change statistics:")

    print(
        f"Mean   : "
        f"{df['price_change'].mean():.2f}"
    )

    print(
        f"Median : "
        f"{df['price_change'].median():.2f}"
    )

    print(
        f"Min    : "
        f"{df['price_change'].min():.2f}"
    )

    print(
        f"Max    : "
        f"{df['price_change'].max():.2f}"
    )

    print(
        f"Std    : "
        f"{df['price_change'].std():.2f}"
    )

    # --------------------------------------------------------
    # Direction distribution
    # --------------------------------------------------------

    print("\nDirection distribution:")

    print(
        df["price_direction"]
        .value_counts()
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_path = os.path.join(
        OUTPUT_DIR,
        f"{market}_change_features_v2.csv"
    )

    df.to_csv(
        output_path,
        index=False
    )

    print(
        f"\nSaved: {output_path}"
    )

    print(
        f"Final rows: {len(df)}"
    )

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("PRICE-CHANGE FEATURE CREATION V2")
    print("=" * 70)

    all_data = []

    for market in MARKETS:

        try:

            df = create_change_dataset(
                market
            )

            all_data.append(df)

        except Exception as e:

            print(
                f"\nERROR processing {market}:"
            )

            print(e)

    # --------------------------------------------------------
    # Combined dataset
    # --------------------------------------------------------

    if all_data:

        combined_df = pd.concat(
            all_data,
            ignore_index=True
        )

        combined_path = os.path.join(
            OUTPUT_DIR,
            "onion_all_markets_change_features_v2.csv"
        )

        combined_df.to_csv(
            combined_path,
            index=False
        )

        print("\n" + "=" * 70)
        print("COMBINED DATASET")
        print("=" * 70)

        print(
            f"Total rows: {len(combined_df)}"
        )

        print(
            f"Saved: {combined_path}"
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()