import os
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

RAW_DIR = "data/raw"
OUTPUT_DIR = "data/processed"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# SELECTED FORECASTING SERIES
# ============================================================
#
# Based on our profiling:
#
# Bareilly -> Red + FAQ
# Bargarh  -> Other + FAQ
# Nagpur   -> Red + FAQ
#
# ============================================================

MARKETS = {
    "Bareilly": {
        "input_file": "onion_bareilly_history.csv",
        "variety": "Red",
        "grade": "FAQ",
        "output_file": "onion_bareilly_model.csv"
    },

    "Bargarh": {
        "input_file": "onion_bargarh_history.csv",
        "variety": "Other",
        "grade": "FAQ",
        "output_file": "onion_bargarh_model.csv"
    },

    "Nagpur": {
        "input_file": "onion_nagpur_history.csv",
        "variety": "Red",
        "grade": "FAQ",
        "output_file": "onion_nagpur_model.csv"
    }
}


# ============================================================
# REQUIRED COLUMNS
# ============================================================

REQUIRED_COLUMNS = [
    "Arrival_Date",
    "Commodity",
    "Commodity_Code",
    "District",
    "Grade",
    "Market",
    "Max_Price",
    "Min_Price",
    "Modal_Price",
    "State",
    "Variety"
]


# ============================================================
# LOAD DATA
# ============================================================

def load_data(market, config):

    path = os.path.join(
        RAW_DIR,
        config["input_file"]
    )

    print("\n" + "=" * 80)
    print(f"LOADING {market}")
    print("=" * 80)

    if not os.path.exists(path):

        print(
            f"ERROR: File not found:\n{path}"
        )

        return None

    df = pd.read_csv(path)

    print(
        f"Raw records: {len(df)}"
    )

    return df


# ============================================================
# CHECK COLUMNS
# ============================================================

def check_columns(df, market):

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:

        print(
            f"ERROR: Missing columns in {market}:"
        )

        print(missing)

        return False

    return True


# ============================================================
# FILTER MARKET
# ============================================================

def filter_market(df, market, config):

    print("\n" + "-" * 80)
    print(f"FILTERING SERIES — {market}")
    print("-" * 80)

    # --------------------------------------------------------
    # Commodity
    # --------------------------------------------------------

    df = df[
        df["Commodity"]
        .astype(str)
        .str.strip()
        .str.lower()
        == "onion"
    ].copy()

    print(
        "After Onion filter:",
        len(df)
    )

    # --------------------------------------------------------
    # Market
    # --------------------------------------------------------

    df = df[
        df["Market"]
        .astype(str)
        .str.strip()
        .str.lower()
        ==
        market.lower()
    ].copy()

    print(
        "After Market filter:",
        len(df)
    )

    # --------------------------------------------------------
    # Variety
    # --------------------------------------------------------

    variety = config["variety"]

    df = df[
        df["Variety"]
        .astype(str)
        .str.strip()
        .str.lower()
        ==
        variety.lower()
    ].copy()

    print(
        f"After Variety = {variety}:",
        len(df)
    )

    # --------------------------------------------------------
    # Grade
    # --------------------------------------------------------

    grade = config["grade"]

    df = df[
        df["Grade"]
        .astype(str)
        .str.strip()
        .str.lower()
        ==
        grade.lower()
    ].copy()

    print(
        f"After Grade = {grade}:",
        len(df)
    )

    return df


# ============================================================
# CONVERT DATA TYPES
# ============================================================

def convert_data_types(df):

    print("\n" + "-" * 80)
    print("CONVERTING DATA TYPES")
    print("-" * 80)

    # Date

    df["date"] = pd.to_datetime(
        df["Arrival_Date"],
        dayfirst=True,
        errors="coerce"
    )

    # Prices

    for column in [
        "Min_Price",
        "Modal_Price",
        "Max_Price"
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    return df


# ============================================================
# REMOVE INVALID DATES
# ============================================================

def remove_invalid_dates(df):

    before = len(df)

    df = df[
        df["date"].notna()
    ].copy()

    removed = before - len(df)

    print(
        "Invalid date rows removed:",
        removed
    )

    return df


# ============================================================
# REMOVE MISSING PRICES
# ============================================================

def remove_missing_prices(df):

    before = len(df)

    df = df.dropna(
        subset=[
            "Min_Price",
            "Modal_Price",
            "Max_Price"
        ]
    ).copy()

    removed = before - len(df)

    print(
        "Rows with missing prices removed:",
        removed
    )

    return df


# ============================================================
# REMOVE NEGATIVE PRICES
# ============================================================

def remove_negative_prices(df):

    before = len(df)

    mask = (
        (df["Min_Price"] >= 0)
        &
        (df["Modal_Price"] >= 0)
        &
        (df["Max_Price"] >= 0)
    )

    df = df[
        mask
    ].copy()

    removed = before - len(df)

    print(
        "Negative price rows removed:",
        removed
    )

    return df


# ============================================================
# REMOVE LOGICALLY INVALID PRICES
# ============================================================

def remove_invalid_price_relationships(df):

    before = len(df)

    # Valid relationship:
    #
    # Min <= Modal <= Max

    valid = (
        (df["Min_Price"] <= df["Modal_Price"])
        &
        (df["Modal_Price"] <= df["Max_Price"])
    )

    invalid_count = (~valid).sum()

    print(
        "Invalid price relationship rows:",
        invalid_count
    )

    df = df[
        valid
    ].copy()

    removed = before - len(df)

    print(
        "Rows removed:",
        removed
    )

    return df


# ============================================================
# REMOVE EXACT DUPLICATES
# ============================================================

def remove_exact_duplicates(df):

    before = len(df)

    duplicates = df.duplicated().sum()

    print(
        "Exact duplicate rows:",
        duplicates
    )

    df = df.drop_duplicates().copy()

    removed = before - len(df)

    print(
        "Duplicate rows removed:",
        removed
    )

    return df


# ============================================================
# CHECK MULTIPLE RECORDS PER DATE
# ============================================================

def analyze_multiple_dates(df, market):

    print("\n" + "-" * 80)
    print(
        f"MULTIPLE RECORDS PER DATE — {market}"
    )
    print("-" * 80)

    counts = (
        df.groupby("date")
        .size()
    )

    multiple_dates = counts[
        counts > 1
    ]

    print(
        "Unique dates:",
        len(counts)
    )

    print(
        "Dates with multiple records:",
        len(multiple_dates)
    )

    if len(multiple_dates) > 0:

        print(
            "\nMaximum records on one date:",
            multiple_dates.max()
        )

        print(
            "\nSample dates with multiple records:"
        )

        print(
            multiple_dates
            .sort_values(
                ascending=False
            )
            .head(10)
            .to_string()
        )

    return counts


# ============================================================
# HANDLE MULTIPLE RECORDS PER DATE
# ============================================================

def aggregate_daily_prices(df):

    print("\n" + "-" * 80)
    print("CREATING ONE DAILY PRICE OBSERVATION")
    print("-" * 80)

    before_dates = df["date"].nunique()

    # --------------------------------------------------------
    # Since the forecasting target is daily modal price,
    # if multiple valid records remain for the same date,
    # aggregate prices by taking the mean.
    #
    # This is done AFTER:
    # - variety filtering
    # - grade filtering
    # - duplicate removal
    # - invalid price removal
    #
    # --------------------------------------------------------

    daily = (
        df.groupby("date")
        .agg(
            min_price=("Min_Price", "mean"),
            modal_price=("Modal_Price", "mean"),
            max_price=("Max_Price", "mean")
        )
        .reset_index()
    )

    after_dates = len(daily)

    print(
        "Unique dates before aggregation:",
        before_dates
    )

    print(
        "Daily observations after aggregation:",
        after_dates
    )

    return daily


# ============================================================
# ADD MARKET INFORMATION
# ============================================================

def add_market_information(
    daily,
    market,
    config
):

    daily["market"] = market

    daily["commodity"] = "Onion"

    daily["variety"] = config["variety"]

    daily["grade"] = config["grade"]

    return daily


# ============================================================
# SORT DATA
# ============================================================

def sort_data(df):

    df = df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    return df


# ============================================================
# FINAL COLUMN ORDER
# ============================================================

def arrange_columns(df):

    columns = [
        "date",
        "market",
        "commodity",
        "variety",
        "grade",
        "min_price",
        "modal_price",
        "max_price"
    ]

    return df[
        columns
    ]


# ============================================================
# FINAL VALIDATION
# ============================================================

def final_validation(df, market):

    print("\n" + "-" * 80)
    print(
        f"FINAL VALIDATION — {market}"
    )
    print("-" * 80)

    print(
        "Total rows:",
        len(df)
    )

    print(
        "Unique dates:",
        df["date"].nunique()
    )

    print(
        "Missing values:"
    )

    print(
        df.isna().sum().to_string()
    )

    print(
        "\nDuplicate dates:",
        df["date"].duplicated().sum()
    )

    # Price validation again

    invalid = (
        (df["min_price"] > df["modal_price"])
        |
        (df["modal_price"] > df["max_price"])
    ).sum()

    print(
        "Invalid price relationships:",
        invalid
    )

    if len(df) > 0:

        print(
            "Start date:",
            df["date"].min().strftime(
                "%Y-%m-%d"
            )
        )

        print(
            "End date:",
            df["date"].max().strftime(
                "%Y-%m-%d"
            )
        )

        print(
            "\nModal price statistics:"
        )

        print(
            df["modal_price"]
            .describe()
            .to_string()
        )


# ============================================================
# PROCESS ONE MARKET
# ============================================================

def process_market(market, config):

    df = load_data(
        market,
        config
    )

    if df is None:

        return None

    # --------------------------------------------------------
    # Check columns
    # --------------------------------------------------------

    if not check_columns(
        df,
        market
    ):

        return None

    # --------------------------------------------------------
    # Filter
    # --------------------------------------------------------

    df = filter_market(
        df,
        market,
        config
    )

    if df.empty:

        print(
            f"No records after filtering {market}."
        )

        return None

    # --------------------------------------------------------
    # Convert data types
    # --------------------------------------------------------

    df = convert_data_types(
        df
    )

    # --------------------------------------------------------
    # Remove invalid dates
    # --------------------------------------------------------

    df = remove_invalid_dates(
        df
    )

    # --------------------------------------------------------
    # Remove missing prices
    # --------------------------------------------------------

    df = remove_missing_prices(
        df
    )

    # --------------------------------------------------------
    # Remove negative prices
    # --------------------------------------------------------

    df = remove_negative_prices(
        df
    )

    # --------------------------------------------------------
    # Remove invalid price relationships
    # --------------------------------------------------------

    df = remove_invalid_price_relationships(
        df
    )

    # --------------------------------------------------------
    # Remove exact duplicates
    # --------------------------------------------------------

    df = remove_exact_duplicates(
        df
    )

    # --------------------------------------------------------
    # Analyze multiple records per date
    # --------------------------------------------------------

    analyze_multiple_dates(
        df,
        market
    )

    # --------------------------------------------------------
    # Create daily series
    # --------------------------------------------------------

    daily = aggregate_daily_prices(
        df
    )

    # --------------------------------------------------------
    # Add metadata
    # --------------------------------------------------------

    daily = add_market_information(
        daily,
        market,
        config
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    daily = sort_data(
        daily
    )

    # --------------------------------------------------------
    # Arrange columns
    # --------------------------------------------------------

    daily = arrange_columns(
        daily
    )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    final_validation(
        daily,
        market
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_path = os.path.join(
        OUTPUT_DIR,
        config["output_file"]
    )

    daily.to_csv(
        output_path,
        index=False
    )

    print(
        f"\nSaved model dataset:"
    )

    print(
        output_path
    )

    return daily


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 80)
    print("CREATING FINAL MODEL DATASETS")
    print("=" * 80)

    processed = {}

    # --------------------------------------------------------
    # Process each market
    # --------------------------------------------------------

    for market, config in MARKETS.items():

        daily = process_market(
            market,
            config
        )

        if daily is not None:

            processed[market] = daily

    # ========================================================
    # COMBINED DATASET
    # ========================================================

    print("\n")
    print("=" * 80)
    print("CREATING COMBINED MULTI-MARKET DATASET")
    print("=" * 80)

    if processed:

        combined = pd.concat(
            processed.values(),
            ignore_index=True
        )

        combined = combined.sort_values(
            [
                "date",
                "market"
            ]
        ).reset_index(
            drop=True
        )

        combined_path = os.path.join(
            OUTPUT_DIR,
            "onion_multi_market_model.csv"
        )

        combined.to_csv(
            combined_path,
            index=False
        )

        print(
            f"Combined rows: {len(combined)}"
        )

        print(
            f"Saved: {combined_path}"
        )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n")
    print("=" * 80)
    print("MODEL DATASET SUMMARY")
    print("=" * 80)

    for market, df in processed.items():

        print(
            f"\n{market}"
        )

        print(
            f"Rows: {len(df)}"
        )

        print(
            f"Dates: "
            f"{df['date'].min().date()} "
            f"→ "
            f"{df['date'].max().date()}"
        )

        print(
            f"Modal price range: "
            f"{df['modal_price'].min()} "
            f"→ "
            f"{df['modal_price'].max()}"
        )

    print("\n")
    print("=" * 80)
    print("MODEL DATASET CREATION COMPLETE")
    print("=" * 80)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()