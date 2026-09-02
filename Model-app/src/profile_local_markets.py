import os
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = "data/raw"

MARKETS = {
    "Nagpur": "onion_nagpur_history.csv",
    "Bareilly": "onion_bareilly_history.csv",
    "Bargarh": "onion_bargarh_history.csv"
}


# ============================================================
# LOAD DATA
# ============================================================

def load_market(market, filename):

    path = os.path.join(DATA_DIR, filename)

    print("\n" + "=" * 80)
    print(f"LOADING: {market}")
    print("=" * 80)

    if not os.path.exists(path):

        print(f"ERROR: File not found:")
        print(path)

        return None

    df = pd.read_csv(path)

    print(f"File: {path}")
    print(f"Raw records: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    return df


# ============================================================
# BASIC INFORMATION
# ============================================================

def basic_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"1. BASIC INFORMATION — {market}")
    print("-" * 80)

    print("Total records:", len(df))

    # Date conversion
    if "Arrival_Date" in df.columns:

        dates = pd.to_datetime(
            df["Arrival_Date"],
            dayfirst=True,
            errors="coerce"
        )

        print("Invalid dates:", dates.isna().sum())
        print("Unique dates:", dates.nunique())

        if dates.notna().any():

            print(
                "Start date:",
                dates.min().strftime("%Y-%m-%d")
            )

            print(
                "End date:",
                dates.max().strftime("%Y-%m-%d")
            )


# ============================================================
# VARIETY ANALYSIS
# ============================================================

def variety_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"2. VARIETY DISTRIBUTION — {market}")
    print("-" * 80)

    if "Variety" not in df.columns:

        print("Variety column not found.")

        return

    counts = (
        df["Variety"]
        .fillna("MISSING")
        .value_counts()
    )

    print(
        counts.to_string()
    )

    print("\nDetailed variety analysis:")

    for variety, count in counts.items():

        subset = df[
            df["Variety"].fillna("MISSING")
            == variety
        ]

        dates = pd.to_datetime(
            subset["Arrival_Date"],
            dayfirst=True,
            errors="coerce"
        )

        unique_dates = dates.nunique()

        print(
            f"{str(variety):30s} "
            f"Records = {count:6d} | "
            f"Unique dates = {unique_dates:6d}"
        )


# ============================================================
# GRADE ANALYSIS
# ============================================================

def grade_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"3. GRADE DISTRIBUTION — {market}")
    print("-" * 80)

    if "Grade" not in df.columns:

        print("Grade column not found.")

        return

    counts = (
        df["Grade"]
        .fillna("MISSING")
        .value_counts()
    )

    print(
        counts.to_string()
    )


# ============================================================
# VARIETY × GRADE ANALYSIS
# ============================================================

def variety_grade_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"4. VARIETY × GRADE COMBINATIONS — {market}")
    print("-" * 80)

    required = [
        "Variety",
        "Grade"
    ]

    for column in required:

        if column not in df.columns:

            print(
                f"{column} column not found."
            )

            return

    combinations = (
        df.groupby(
            [
                "Variety",
                "Grade"
            ],
            dropna=False
        )
        .agg(
            records=("Arrival_Date", "size"),
            unique_dates=("Arrival_Date", "nunique")
        )
        .reset_index()
        .sort_values(
            "records",
            ascending=False
        )
    )

    print(
        combinations.to_string(
            index=False
        )
    )


# ============================================================
# DUPLICATE ANALYSIS
# ============================================================

def duplicate_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"5. DUPLICATE ANALYSIS — {market}")
    print("-" * 80)

    exact_duplicates = df.duplicated().sum()

    print(
        "Exact duplicate rows:",
        exact_duplicates
    )

    # Business key
    business_key = [
        "Arrival_Date",
        "Commodity",
        "State",
        "District",
        "Market",
        "Variety",
        "Grade"
    ]

    available = [
        column
        for column in business_key
        if column in df.columns
    ]

    if available:

        business_duplicates = df.duplicated(
            subset=available
        ).sum()

        print(
            "Business-key duplicate rows:",
            business_duplicates
        )

        print(
            "Business key:",
            available
        )


# ============================================================
# PRICE VALIDATION
# ============================================================

def price_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"6. PRICE VALIDATION — {market}")
    print("-" * 80)

    price_columns = [
        "Min_Price",
        "Modal_Price",
        "Max_Price"
    ]

    missing_columns = [
        column
        for column in price_columns
        if column not in df.columns
    ]

    if missing_columns:

        print(
            "Missing columns:",
            missing_columns
        )

        return

    price_df = df.copy()

    for column in price_columns:

        price_df[column] = pd.to_numeric(
            price_df[column],
            errors="coerce"
        )

    # Missing
    missing = (
        price_df[price_columns]
        .isna()
        .any(axis=1)
        .sum()
    )

    # Logical errors
    min_greater_modal = (
        price_df["Min_Price"]
        >
        price_df["Modal_Price"]
    ).sum()

    modal_greater_max = (
        price_df["Modal_Price"]
        >
        price_df["Max_Price"]
    ).sum()

    min_greater_max = (
        price_df["Min_Price"]
        >
        price_df["Max_Price"]
    ).sum()

    negative = (
        price_df[price_columns]
        < 0
    ).any(axis=1).sum()

    print(
        "Missing price records:",
        missing
    )

    print(
        "Min > Modal:",
        min_greater_modal
    )

    print(
        "Modal > Max:",
        modal_greater_max
    )

    print(
        "Min > Max:",
        min_greater_max
    )

    print(
        "Negative price records:",
        negative
    )

    # Total logically invalid
    invalid_mask = (
        price_df["Min_Price"]
        >
        price_df["Modal_Price"]
    ) | (
        price_df["Modal_Price"]
        >
        price_df["Max_Price"]
    ) | (
        price_df["Min_Price"]
        >
        price_df["Max_Price"]
    ) | (
        price_df[price_columns]
        < 0
    ).any(axis=1)

    print(
        "Total logically invalid:",
        invalid_mask.sum()
    )


# ============================================================
# YEARLY ANALYSIS
# ============================================================

def yearly_analysis(df, market):

    print("\n" + "-" * 80)
    print(f"7. YEARLY RECORDS — {market}")
    print("-" * 80)

    if "Arrival_Date" not in df.columns:

        return

    dates = pd.to_datetime(
        df["Arrival_Date"],
        dayfirst=True,
        errors="coerce"
    )

    yearly = (
        dates.dt.year
        .value_counts()
        .sort_index()
    )

    print(
        yearly.to_string()
    )

    print("\nRecent years:")

    for year in range(2021, 2026):

        count = yearly.get(
            year,
            0
        )

        print(
            f"{year}: {count}"
        )


# ============================================================
# VARIETY × GRADE × RECENT DATA
# ============================================================

def recent_combination_analysis(df, market):

    print("\n" + "-" * 80)
    print(
        f"8. VARIETY × GRADE × RECENT DATA — {market}"
    )
    print("-" * 80)

    required = [
        "Arrival_Date",
        "Variety",
        "Grade"
    ]

    if not all(
        column in df.columns
        for column in required
    ):

        print(
            "Required columns missing."
        )

        return

    temp = df.copy()

    temp["Arrival_Date"] = pd.to_datetime(
        temp["Arrival_Date"],
        dayfirst=True,
        errors="coerce"
    )

    temp = temp[
        temp["Arrival_Date"]
        >= pd.Timestamp("2021-01-01")
    ]

    summary = (
        temp.groupby(
            [
                "Variety",
                "Grade"
            ],
            dropna=False
        )
        .agg(
            records=("Arrival_Date", "size"),
            unique_dates=("Arrival_Date", "nunique"),
            first_date=("Arrival_Date", "min"),
            last_date=("Arrival_Date", "max")
        )
        .reset_index()
        .sort_values(
            "records",
            ascending=False
        )
    )

    print(
        summary.to_string(
            index=False
        )
    )


# ============================================================
# TOP SERIES CANDIDATES
# ============================================================

def identify_candidates(df, market):

    print("\n" + "-" * 80)
    print(
        f"9. POTENTIAL FORECASTING SERIES — {market}"
    )
    print("-" * 80)

    required = [
        "Arrival_Date",
        "Variety",
        "Grade"
    ]

    if not all(
        column in df.columns
        for column in required
    ):

        return

    temp = df.copy()

    temp["Arrival_Date"] = pd.to_datetime(
        temp["Arrival_Date"],
        dayfirst=True,
        errors="coerce"
    )

    # Only recent period
    temp = temp[
        temp["Arrival_Date"]
        >= pd.Timestamp("2021-01-01")
    ]

    candidates = (
        temp.groupby(
            [
                "Variety",
                "Grade"
            ],
            dropna=False
        )
        .agg(
            records=("Arrival_Date", "size"),
            unique_dates=("Arrival_Date", "nunique")
        )
        .reset_index()
    )

    candidates["date_coverage_ratio"] = (
        candidates["unique_dates"]
        /
        candidates["records"]
    )

    candidates = candidates.sort_values(
        [
            "unique_dates",
            "records"
        ],
        ascending=False
    )

    print(
        candidates.to_string(
            index=False
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 80)
    print("LOCAL MARKET + VARIETY + GRADE PROFILING")
    print("=" * 80)

    for market, filename in MARKETS.items():

        df = load_market(
            market,
            filename
        )

        if df is None:

            continue

        # ----------------------------------------------------
        # 1. Basic
        # ----------------------------------------------------

        basic_analysis(
            df,
            market
        )

        # ----------------------------------------------------
        # 2. Variety
        # ----------------------------------------------------

        variety_analysis(
            df,
            market
        )

        # ----------------------------------------------------
        # 3. Grade
        # ----------------------------------------------------

        grade_analysis(
            df,
            market
        )

        # ----------------------------------------------------
        # 4. Variety × Grade
        # ----------------------------------------------------

        variety_grade_analysis(
            df,
            market
        )

        # ----------------------------------------------------
        # 5. Duplicates
        # ----------------------------------------------------

        duplicate_analysis(
            df,
            market
        )

        # ----------------------------------------------------
        # 6. Price validation
        # ----------------------------------------------------

        price_analysis(
            df,
            market
        )

        # ----------------------------------------------------
        # 7. Yearly
        # ----------------------------------------------------

        yearly_analysis(
            df,
            market
        )

        # ----------------------------------------------------
        # 8. Recent combinations
        # ----------------------------------------------------

        recent_combination_analysis(
            df,
            market
        )

        # ----------------------------------------------------
        # 9. Potential series
        # ----------------------------------------------------

        identify_candidates(
            df,
            market
        )

    # ========================================================
    # COMPLETE
    # ========================================================

    print("\n")
    print("=" * 80)
    print("LOCAL PROFILING COMPLETE")
    print("=" * 80)

    print(
        "\nNo API was used."
    )

    print(
        "All analysis was performed "
        "on the locally saved CSV files."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()