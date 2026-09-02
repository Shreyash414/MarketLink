import os
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

MARKETS = [
    "bareilly",
    "bargarh",
    "nagpur"
]

INPUT_DIR = "data/processed/change_features"

OUTPUT_DIR = "data/processed/change_splits"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# SPLIT ONE MARKET
# ============================================================

def split_market(market):

    print("\n" + "=" * 70)
    print(f"SPLITTING: {market.upper()}")
    print("=" * 70)

    input_path = os.path.join(
        INPUT_DIR,
        f"{market}_change_features.csv"
    )

    df = pd.read_csv(
        input_path
    )

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

    total_rows = len(df)

    # --------------------------------------------------------
    # Calculate split points
    # --------------------------------------------------------

    train_end = int(
        total_rows * 0.70
    )

    validation_end = int(
        total_rows * 0.85
    )

    # --------------------------------------------------------
    # Create splits
    # --------------------------------------------------------

    train_df = df.iloc[
        :train_end
    ].copy()

    validation_df = df.iloc[
        train_end:validation_end
    ].copy()

    test_df = df.iloc[
        validation_end:
    ].copy()

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    train_path = os.path.join(
        OUTPUT_DIR,
        f"{market}_train.csv"
    )

    validation_path = os.path.join(
        OUTPUT_DIR,
        f"{market}_validation.csv"
    )

    test_path = os.path.join(
        OUTPUT_DIR,
        f"{market}_test.csv"
    )

    train_df.to_csv(
        train_path,
        index=False
    )

    validation_df.to_csv(
        validation_path,
        index=False
    )

    test_df.to_csv(
        test_path,
        index=False
    )

    # --------------------------------------------------------
    # Print information
    # --------------------------------------------------------

    print(f"Total rows      : {total_rows}")

    print(
        f"Train rows      : {len(train_df)}"
    )

    print(
        f"Validation rows : {len(validation_df)}"
    )

    print(
        f"Test rows       : {len(test_df)}"
    )

    print("\nDate ranges:")

    print(
        f"Train      : "
        f"{train_df['date'].min().date()} "
        f"→ "
        f"{train_df['date'].max().date()}"
    )

    print(
        f"Validation : "
        f"{validation_df['date'].min().date()} "
        f"→ "
        f"{validation_df['date'].max().date()}"
    )

    print(
        f"Test       : "
        f"{test_df['date'].min().date()} "
        f"→ "
        f"{test_df['date'].max().date()}"
    )

    # --------------------------------------------------------
    # Check chronological order
    # --------------------------------------------------------

    if (
        train_df["date"].max()
        < validation_df["date"].min()
        and
        validation_df["date"].max()
        < test_df["date"].min()
    ):

        print(
            "\n✓ Chronological split is valid."
        )

    else:

        print(
            "\n✗ ERROR: Date overlap detected!"
        )

    # --------------------------------------------------------
    # Check target
    # --------------------------------------------------------

    print("\nPrice-change statistics:")

    print(
        f"Train mean change      : "
        f"{train_df['price_change'].mean():.2f}"
    )

    print(
        f"Validation mean change : "
        f"{validation_df['price_change'].mean():.2f}"
    )

    print(
        f"Test mean change       : "
        f"{test_df['price_change'].mean():.2f}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("PRICE-CHANGE TIME-SERIES SPLIT")
    print("=" * 70)

    for market in MARKETS:

        try:

            split_market(
                market
            )

        except Exception as e:

            print(
                f"\nERROR splitting {market}:"
            )

            print(e)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()