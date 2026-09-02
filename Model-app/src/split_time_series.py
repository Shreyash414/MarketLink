import os
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

FEATURE_DIR = "data/processed/features"
SPLIT_DIR = "data/processed/splits"

os.makedirs(SPLIT_DIR, exist_ok=True)


DATASETS = {
    "Bareilly": "bareilly_features.csv",
    "Bargarh": "bargarh_features.csv",
    "Nagpur": "nagpur_features.csv"
}


# ============================================================
# SPLIT RATIO
# ============================================================

TRAIN_RATIO = 0.70
VALIDATION_RATIO = 0.15
TEST_RATIO = 0.15


# ============================================================
# LOAD DATA
# ============================================================

def load_data(market, filename):

    path = os.path.join(
        FEATURE_DIR,
        filename
    )

    print("\n" + "=" * 80)
    print(f"LOADING {market}")
    print("=" * 80)

    df = pd.read_csv(path)

    df["date"] = pd.to_datetime(
        df["date"]
    )

    # Always sort chronologically

    df = df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    print(
        "Total rows:",
        len(df)
    )

    print(
        "Date range:",
        df["date"].min().date(),
        "→",
        df["date"].max().date()
    )

    return df


# ============================================================
# TIME SERIES SPLIT
# ============================================================

def split_data(df):

    n = len(df)

    train_end = int(
        n * TRAIN_RATIO
    )

    validation_end = int(
        n *
        (
            TRAIN_RATIO
            +
            VALIDATION_RATIO
        )
    )

    train = df.iloc[
        :train_end
    ].copy()

    validation = df.iloc[
        train_end:validation_end
    ].copy()

    test = df.iloc[
        validation_end:
    ].copy()

    return train, validation, test


# ============================================================
# VALIDATE SPLIT
# ============================================================

def validate_split(
    train,
    validation,
    test,
    market
):

    print("\n" + "-" * 80)
    print(
        f"SPLIT VALIDATION — {market}"
    )
    print("-" * 80)

    # --------------------------------------------------------
    # Row counts
    # --------------------------------------------------------

    print(
        "Train rows:",
        len(train)
    )

    print(
        "Validation rows:",
        len(validation)
    )

    print(
        "Test rows:",
        len(test)
    )

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    print("\nDate ranges:")

    print(
        "Train:",
        train["date"].min().date(),
        "→",
        train["date"].max().date()
    )

    print(
        "Validation:",
        validation["date"].min().date(),
        "→",
        validation["date"].max().date()
    )

    print(
        "Test:",
        test["date"].min().date(),
        "→",
        test["date"].max().date()
    )

    # --------------------------------------------------------
    # Check chronological order
    # --------------------------------------------------------

    chronological = (
        train["date"].max()
        <
        validation["date"].min()
        and
        validation["date"].max()
        <
        test["date"].min()
    )

    print(
        "\nChronological separation:",
        chronological
    )

    # --------------------------------------------------------
    # Check date overlap
    # --------------------------------------------------------

    train_dates = set(
        train["date"]
    )

    validation_dates = set(
        validation["date"]
    )

    test_dates = set(
        test["date"]
    )

    train_validation_overlap = (
        train_dates &
        validation_dates
    )

    validation_test_overlap = (
        validation_dates &
        test_dates
    )

    train_test_overlap = (
        train_dates &
        test_dates
    )

    print(
        "Train/Validation overlap:",
        len(train_validation_overlap)
    )

    print(
        "Validation/Test overlap:",
        len(validation_test_overlap)
    )

    print(
        "Train/Test overlap:",
        len(train_test_overlap)
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    if (
        chronological
        and
        len(train_validation_overlap) == 0
        and
        len(validation_test_overlap) == 0
        and
        len(train_test_overlap) == 0
    ):

        print(
            "\nSTATUS: SPLIT IS VALID"
        )

    else:

        print(
            "\nSTATUS: SPLIT NEEDS INVESTIGATION"
        )


# ============================================================
# SAVE SPLITS
# ============================================================

def save_split(
    df,
    market,
    split_name
):

    filename = (
        f"{market.lower()}_"
        f"{split_name}.csv"
    )

    path = os.path.join(
        SPLIT_DIR,
        filename
    )

    df.to_csv(
        path,
        index=False
    )

    print(
        "Saved:",
        path
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

    train, validation, test = split_data(
        df
    )

    validate_split(
        train,
        validation,
        test,
        market
    )

    print("\nSaving files...")

    save_split(
        train,
        market,
        "train"
    )

    save_split(
        validation,
        market,
        "validation"
    )

    save_split(
        test,
        market,
        "test"
    )

    return train, validation, test


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 80)
    print("TIME SERIES TRAIN / VALIDATION / TEST SPLIT")
    print("=" * 80)

    for market, filename in DATASETS.items():

        process_market(
            market,
            filename
        )

    print("\n")
    print("=" * 80)
    print("TIME SERIES SPLITTING COMPLETE")
    print("=" * 80)

    print(
        "\nFiles saved in:"
    )

    print(
        SPLIT_DIR
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()