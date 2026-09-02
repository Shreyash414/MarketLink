import os
import pandas as pd


MARKETS = [
    "bareilly",
    "bargarh",
    "nagpur"
]

INPUT_DIR = "data/processed/change_features_v2"

OUTPUT_DIR = "data/processed/change_splits_v2"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


def split_market(market):

    print("\n" + "=" * 70)
    print(f"SPLITTING CHANGE FEATURES V2: {market.upper()}")
    print("=" * 70)

    input_path = os.path.join(
        INPUT_DIR,
        f"{market}_change_features_v2.csv"
    )

    df = pd.read_csv(input_path)

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df = df.sort_values(
        "date"
    ).reset_index(drop=True)

    total_rows = len(df)

    train_end = int(
        total_rows * 0.70
    )

    validation_end = int(
        total_rows * 0.85
    )

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

    print(
        f"Total rows      : {total_rows}"
    )

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
    # Validate chronology
    # --------------------------------------------------------

    valid_split = (
        train_df["date"].max()
        < validation_df["date"].min()
        and
        validation_df["date"].max()
        < test_df["date"].min()
    )

    if valid_split:
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

    print("\nPrice-change target statistics:")

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

    # --------------------------------------------------------
    # Check feature count
    # --------------------------------------------------------

    excluded = [
        "date",
        "target_price",
        "price_change",
        "price_change_pct",
        "price_direction",
        "market",
        "commodity",
        "variety",
        "grade"
    ]

    features = [
        col for col in df.columns
        if col not in excluded
        and pd.api.types.is_numeric_dtype(df[col])
    ]

    print(
        f"\nNumber of usable features: "
        f"{len(features)}"
    )


def main():

    print("=" * 70)
    print("CHANGE FEATURES V2 - TIME SERIES SPLIT")
    print("=" * 70)

    for market in MARKETS:

        try:

            split_market(market)

        except Exception as e:

            print(
                f"\nERROR splitting {market}:"
            )

            print(e)


if __name__ == "__main__":
    main()