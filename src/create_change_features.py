import os
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

MARKETS = {
    "bareilly": {
        "input": "data/processed/onion_bareilly_model.csv"
    },

    "bargarh": {
        "input": "data/processed/onion_bargarh_model.csv"
    },

    "nagpur": {
        "input": "data/processed/onion_nagpur_model.csv"
    }
}

OUTPUT_DIR = "data/processed/change_features"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# CREATE CHANGE FEATURES FOR ONE MARKET
# ============================================================

def create_change_features(market, input_path):

    print("\n" + "=" * 70)
    print(f"CREATING PRICE-CHANGE DATASET: {market.upper()}")
    print("=" * 70)

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    df = pd.read_csv(input_path)

    print(f"Input rows: {len(df)}")

    # --------------------------------------------------------
    # Convert date
    # --------------------------------------------------------

    df["date"] = pd.to_datetime(
        df["date"]
    )

    # Sort chronologically
    df = df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Current modal price
    # --------------------------------------------------------

    # Make sure modal price is numeric

    df["modal_price"] = pd.to_numeric(
        df["modal_price"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Create target
    # --------------------------------------------------------

    # Next observed market price

    df["next_price"] = (
        df["modal_price"].shift(-1)
    )

    # Price change:
    #
    # next price - current price
    #
    # Example:
    # current = 2000
    # next    = 2150
    # change  = +150

    df["price_change"] = (
        df["next_price"]
        - df["modal_price"]
    )

    # --------------------------------------------------------
    # Percentage price change
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
    # Future price direction
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
    # Remove rows where target cannot be created
    # --------------------------------------------------------

    before = len(df)

    df = df.dropna(
        subset=[
            "next_price",
            "price_change"
        ]
    ).copy()

    after = len(df)

    print(
        f"Removed rows without future price: "
        f"{before - after}"
    )

    # --------------------------------------------------------
    # Check for invalid values
    # --------------------------------------------------------

    print("\nTarget statistics:")

    print(
        f"Mean price change   : "
        f"{df['price_change'].mean():.2f}"
    )

    print(
        f"Median price change : "
        f"{df['price_change'].median():.2f}"
    )

    print(
        f"Minimum change      : "
        f"{df['price_change'].min():.2f}"
    )

    print(
        f"Maximum change      : "
        f"{df['price_change'].max():.2f}"
    )

    print(
        f"Std deviation       : "
        f"{df['price_change'].std():.2f}"
    )

    # --------------------------------------------------------
    # Direction distribution
    # --------------------------------------------------------

    print("\nPrice direction:")

    direction_counts = (
        df["price_direction"]
        .value_counts()
    )

    print(
        direction_counts
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_path = os.path.join(
        OUTPUT_DIR,
        f"{market}_change_features.csv"
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

    # --------------------------------------------------------
    # Show latest observations
    # --------------------------------------------------------

    print("\nLatest observations:")

    columns_to_show = [
        "date",
        "modal_price",
        "next_price",
        "price_change",
        "price_change_pct",
        "price_direction"
    ]

    print(
        df[columns_to_show]
        .tail(10)
        .to_string(index=False)
    )

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("PRICE-CHANGE FEATURE CREATION")
    print("=" * 70)

    all_data = []

    for market, config in MARKETS.items():

        input_path = config["input"]

        try:

            df = create_change_features(
                market,
                input_path
            )

            all_data.append(df)

        except Exception as e:

            print(
                f"\nERROR processing {market}:"
            )

            print(e)

    # ========================================================
    # CREATE COMBINED DATASET
    # ========================================================

    if all_data:

        combined_df = pd.concat(
            all_data,
            ignore_index=True
        )

        combined_path = os.path.join(
            OUTPUT_DIR,
            "onion_all_markets_change_features.csv"
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