import pandas as pd
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

INPUT_DIR = Path(
    "data/processed/features_v3"
)

OUTPUT_DIR = Path(
    "data/processed/splits_v3"
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
# SPLIT FUNCTION
# ============================================================

def split_market(df, market):

    print("\n")
    print("=" * 70)
    print(f"V3 CHRONOLOGICAL SPLIT: {market.upper()}")
    print("=" * 70)

    # --------------------------------------------------------
    # SORT BY DATE
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
    # REMOVE ANY DUPLICATE DATES
    # --------------------------------------------------------

    duplicate_dates = df["date"].duplicated().sum()

    print(
        f"Duplicate dates: {duplicate_dates}"
    )

    if duplicate_dates > 0:

        print(
            "WARNING: Duplicate dates found."
        )

        df = df.drop_duplicates(
            subset=["date"],
            keep="last"
        ).reset_index(
            drop=True
        )

    # --------------------------------------------------------
    # TOTAL ROWS
    # --------------------------------------------------------

    n = len(df)

    train_end = int(
        n * 0.70
    )

    validation_end = int(
        n * 0.85
    )

    # --------------------------------------------------------
    # SPLIT
    # --------------------------------------------------------

    train = df.iloc[
        :train_end
    ].copy()

    validation = df.iloc[
        train_end:validation_end
    ].copy()

    test = df.iloc[
        validation_end:
    ].copy()

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    print(
        f"\nTotal rows      : {n}"
    )

    print(
        f"Train rows      : {len(train)} "
        f"({len(train)/n*100:.2f}%)"
    )

    print(
        f"Validation rows : {len(validation)} "
        f"({len(validation)/n*100:.2f}%)"
    )

    print(
        f"Test rows       : {len(test)} "
        f"({len(test)/n*100:.2f}%)"
    )

    # --------------------------------------------------------
    # DATE RANGES
    # --------------------------------------------------------

    print("\nDate ranges:")

    print(
        f"Train      : "
        f"{train['date'].min().date()} "
        f"-> "
        f"{train['date'].max().date()}"
    )

    print(
        f"Validation : "
        f"{validation['date'].min().date()} "
        f"-> "
        f"{validation['date'].max().date()}"
    )

    print(
        f"Test       : "
        f"{test['date'].min().date()} "
        f"-> "
        f"{test['date'].max().date()}"
    )

    # --------------------------------------------------------
    # CHRONOLOGICAL VALIDATION
    # --------------------------------------------------------

    valid_split = True

    if train["date"].max() >= validation["date"].min():
        print(
            "ERROR: Train/validation overlap!"
        )
        valid_split = False

    if validation["date"].max() >= test["date"].min():
        print(
            "ERROR: Validation/test overlap!"
        )
        valid_split = False

    if valid_split:

        print(
            "\n✓ Chronological split is valid."
        )

    # --------------------------------------------------------
    # TARGET STATISTICS
    # --------------------------------------------------------

    if "price_change" in df.columns:

        print("\nPrice-change means:")

        print(
            f"Train      : "
            f"{train['price_change'].mean():.2f}"
        )

        print(
            f"Validation : "
            f"{validation['price_change'].mean():.2f}"
        )

        print(
            f"Test       : "
            f"{test['price_change'].mean():.2f}"
        )

    # --------------------------------------------------------
    # FEATURE COUNT
    # --------------------------------------------------------

    excluded = [
        "date",
        "target_price",
        "price_change",
        "price_change_pct",
        "price_direction"
    ]

    features = [
        col
        for col in df.columns
        if col not in excluded
    ]

    print(
        f"\nNumber of features: "
        f"{len(features)}"
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    train_file = (
        OUTPUT_DIR /
        f"{market}_train.csv"
    )

    validation_file = (
        OUTPUT_DIR /
        f"{market}_validation.csv"
    )

    test_file = (
        OUTPUT_DIR /
        f"{market}_test.csv"
    )

    train.to_csv(
        train_file,
        index=False
    )

    validation.to_csv(
        validation_file,
        index=False
    )

    test.to_csv(
        test_file,
        index=False
    )

    print("\nSaved:")

    print(
        f"  {train_file}"
    )

    print(
        f"  {validation_file}"
    )

    print(
        f"  {test_file}"
    )

    return train, validation, test


# ============================================================
# PROCESS ALL MARKETS
# ============================================================

all_splits = {}


for market in markets:

    input_file = (
        INPUT_DIR /
        f"{market}_features_v3.csv"
    )

    if not input_file.exists():

        raise FileNotFoundError(
            f"File not found: {input_file}"
        )

    df = pd.read_csv(
        input_file
    )

    train, validation, test = split_market(
        df,
        market
    )

    all_splits[market] = {
        "train": train,
        "validation": validation,
        "test": test
    }


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("V3 SPLITTING COMPLETE")
print("=" * 70)

for market in markets:

    train = all_splits[market]["train"]
    validation = all_splits[market]["validation"]
    test = all_splits[market]["test"]

    print(
        f"\n{market.upper()}"
    )

    print(
        f"  Train      : {len(train)}"
    )

    print(
        f"  Validation : {len(validation)}"
    )

    print(
        f"  Test       : {len(test)}"
    )

print("\nOutput directory:")
print(OUTPUT_DIR)