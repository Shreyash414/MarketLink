import os
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

PROCESSED_DIR = "data/processed"

DATASETS = {
    "Bareilly": "onion_bareilly_model.csv",
    "Bargarh": "onion_bargarh_model.csv",
    "Nagpur": "onion_nagpur_model.csv"
}


# ============================================================
# LOAD DATA
# ============================================================

def load_dataset(market, filename):

    path = os.path.join(
        PROCESSED_DIR,
        filename
    )

    print("\n" + "=" * 80)
    print(f"LOADING {market}")
    print("=" * 80)

    if not os.path.exists(path):

        print(f"ERROR: File not found: {path}")

        return None

    df = pd.read_csv(path)

    print("Rows:", len(df))
    print("Columns:", list(df.columns))

    return df


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

def check_required_columns(df, market):

    print("\n" + "-" * 80)
    print("1. COLUMN VALIDATION")
    print("-" * 80)

    required = [
        "date",
        "market",
        "commodity",
        "variety",
        "grade",
        "min_price",
        "modal_price",
        "max_price"
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:

        print("Missing columns:", missing)

        return False

    print("All required columns are present.")

    return True


# ============================================================
# DATA TYPE VALIDATION
# ============================================================

def validate_data_types(df):

    print("\n" + "-" * 80)
    print("2. DATA TYPE VALIDATION")
    print("-" * 80)

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    price_columns = [
        "min_price",
        "modal_price",
        "max_price"
    ]

    for column in price_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    print("\nData types:")

    print(
        df[
            [
                "date",
                "min_price",
                "modal_price",
                "max_price"
            ]
        ]
        .dtypes
        .to_string()
    )

    return df


# ============================================================
# MISSING VALUE CHECK
# ============================================================

def check_missing_values(df):

    print("\n" + "-" * 80)
    print("3. MISSING VALUE CHECK")
    print("-" * 80)

    missing = df.isna().sum()

    print(
        missing.to_string()
    )

    total_missing = missing.sum()

    print(
        "\nTotal missing values:",
        total_missing
    )

    return total_missing


# ============================================================
# DUPLICATE DATE CHECK
# ============================================================

def check_duplicate_dates(df):

    print("\n" + "-" * 80)
    print("4. DUPLICATE DATE CHECK")
    print("-" * 80)

    duplicate_dates = df[
        df["date"].duplicated(
            keep=False
        )
    ]

    count = duplicate_dates["date"].nunique()

    print(
        "Dates appearing more than once:",
        count
    )

    if count > 0:

        print(
            "\nSample duplicate dates:"
        )

        print(
            duplicate_dates[
                [
                    "date",
                    "modal_price"
                ]
            ]
            .sort_values("date")
            .head(20)
            .to_string(index=False)
        )

    return count


# ============================================================
# DATE ORDER CHECK
# ============================================================

def check_date_order(df):

    print("\n" + "-" * 80)
    print("5. DATE ORDER CHECK")
    print("-" * 80)

    is_sorted = df["date"].is_monotonic_increasing

    print(
        "Dates sorted:",
        is_sorted
    )

    if not is_sorted:

        print(
            "WARNING: Dates are not sorted."
        )

    return is_sorted


# ============================================================
# PRICE LOGIC CHECK
# ============================================================

def check_price_logic(df):

    print("\n" + "-" * 80)
    print("6. PRICE LOGIC CHECK")
    print("-" * 80)

    min_greater_modal = (
        df["min_price"]
        >
        df["modal_price"]
    )

    modal_greater_max = (
        df["modal_price"]
        >
        df["max_price"]
    )

    min_greater_max = (
        df["min_price"]
        >
        df["max_price"]
    )

    negative_prices = (
        (df["min_price"] < 0)
        |
        (df["modal_price"] < 0)
        |
        (df["max_price"] < 0)
    )

    print(
        "Min > Modal:",
        min_greater_modal.sum()
    )

    print(
        "Modal > Max:",
        modal_greater_max.sum()
    )

    print(
        "Min > Max:",
        min_greater_max.sum()
    )

    print(
        "Negative prices:",
        negative_prices.sum()
    )

    invalid = (
        min_greater_modal
        |
        modal_greater_max
        |
        min_greater_max
        |
        negative_prices
    )

    print(
        "Total logically invalid rows:",
        invalid.sum()
    )

    return invalid.sum()


# ============================================================
# PRICE STATISTICS
# ============================================================

def price_statistics(df, market):

    print("\n" + "-" * 80)
    print(f"7. PRICE STATISTICS — {market}")
    print("-" * 80)

    columns = [
        "min_price",
        "modal_price",
        "max_price"
    ]

    print(
        df[columns]
        .describe()
        .round(2)
        .to_string()
    )


# ============================================================
# PRICE RANGE CHECK
# ============================================================

def check_price_range(df):

    print("\n" + "-" * 80)
    print("8. PRICE RANGE")
    print("-" * 80)

    for column in [
        "min_price",
        "modal_price",
        "max_price"
    ]:

        print(
            f"{column}: "
            f"{df[column].min()} → "
            f"{df[column].max()}"
        )


# ============================================================
# DATE COVERAGE
# ============================================================

def date_coverage(df, market):

    print("\n" + "-" * 80)
    print(f"9. DATE COVERAGE — {market}")
    print("-" * 80)

    start = df["date"].min()
    end = df["date"].max()

    calendar_days = (
        end - start
    ).days + 1

    observations = len(df)

    coverage = (
        observations /
        calendar_days
    ) * 100

    print(
        "First observation:",
        start.date()
    )

    print(
        "Last observation:",
        end.date()
    )

    print(
        "Calendar days:",
        calendar_days
    )

    print(
        "Actual observations:",
        observations
    )

    print(
        f"Observation/calendar-day ratio: "
        f"{coverage:.2f}%"
    )

    return {
        "start": start,
        "end": end,
        "calendar_days": calendar_days,
        "observations": observations,
        "coverage": coverage
    }


# ============================================================
# GAP ANALYSIS
# ============================================================

def gap_analysis(df):

    print("\n" + "-" * 80)
    print("10. DATE GAP ANALYSIS")
    print("-" * 80)

    dates = (
        df["date"]
        .drop_duplicates()
        .sort_values()
    )

    gaps = (
        dates
        .diff()
        .dt.days
        .dropna()
    )

    if gaps.empty:

        print("Not enough dates for gap analysis.")

        return None

    print(
        "Mean gap:",
        round(gaps.mean(), 2),
        "days"
    )

    print(
        "Median gap:",
        round(gaps.median(), 2),
        "days"
    )

    print(
        "Maximum gap:",
        gaps.max(),
        "days"
    )

    print(
        "Gaps > 7 days:",
        (gaps > 7).sum()
    )

    print(
        "Gaps > 30 days:",
        (gaps > 30).sum()
    )

    print(
        "Gaps > 90 days:",
        (gaps > 90).sum()
    )

    print(
        "\nLargest gaps:"
    )

    largest = (
        gaps
        .sort_values(
            ascending=False
        )
        .head(10)
    )

    print(
        largest.to_string()
    )

    return gaps


# ============================================================
# YEARLY DATA COUNT
# ============================================================

def yearly_counts(df):

    print("\n" + "-" * 80)
    print("11. YEARLY OBSERVATION COUNT")
    print("-" * 80)

    yearly = (
        df.groupby(
            df["date"].dt.year
        )
        .size()
    )

    print(
        yearly.to_string()
    )

    return yearly


# ============================================================
# RECENT DATA CHECK
# ============================================================

def recent_data_check(df):

    print("\n" + "-" * 80)
    print("12. RECENT DATA AVAILABILITY")
    print("-" * 80)

    latest = df["date"].max()

    print(
        "Latest observation:",
        latest.date()
    )

    # Last 5 years

    five_year_start = (
        latest
        - pd.DateOffset(years=5)
    )

    recent_5_years = df[
        df["date"] >= five_year_start
    ]

    print(
        "Observations in latest 5 years:",
        len(recent_5_years)
    )

    # Last 3 years

    three_year_start = (
        latest
        - pd.DateOffset(years=3)
    )

    recent_3_years = df[
        df["date"] >= three_year_start
    ]

    print(
        "Observations in latest 3 years:",
        len(recent_3_years)
    )

    # Last year

    one_year_start = (
        latest
        - pd.DateOffset(years=1)
    )

    recent_1_year = df[
        df["date"] >= one_year_start
    ]

    print(
        "Observations in latest 1 year:",
        len(recent_1_year)
    )

    return {
        "last_5_years": len(recent_5_years),
        "last_3_years": len(recent_3_years),
        "last_1_year": len(recent_1_year)
    }


# ============================================================
# YEARLY PRICE TREND
# ============================================================

def yearly_price_statistics(df):

    print("\n" + "-" * 80)
    print("13. YEARLY MODAL PRICE STATISTICS")
    print("-" * 80)

    yearly = (
        df.groupby(
            df["date"].dt.year
        )["modal_price"]
        .agg(
            [
                "count",
                "mean",
                "median",
                "min",
                "max"
            ]
        )
        .round(2)
    )

    print(
        yearly.to_string()
    )

    return yearly


# ============================================================
# EXTREME OUTLIER CHECK
# ============================================================

def outlier_check(df, market):

    print("\n" + "-" * 80)
    print(f"14. OUTLIER CHECK — {market}")
    print("-" * 80)

    price = df["modal_price"]

    q1 = price.quantile(0.25)
    q3 = price.quantile(0.75)

    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outliers = df[
        (price < lower_bound)
        |
        (price > upper_bound)
    ].copy()

    print(
        "Q1:",
        round(q1, 2)
    )

    print(
        "Q3:",
        round(q3, 2)
    )

    print(
        "IQR:",
        round(iqr, 2)
    )

    print(
        "Lower bound:",
        round(lower_bound, 2)
    )

    print(
        "Upper bound:",
        round(upper_bound, 2)
    )

    print(
        "Potential IQR outliers:",
        len(outliers)
    )

    if len(outliers) > 0:

        print(
            "\nHighest price observations:"
        )

        print(
            outliers
            .sort_values(
                "modal_price",
                ascending=False
            )
            [
                [
                    "date",
                    "modal_price"
                ]
            ]
            .head(10)
            .to_string(index=False)
        )

    return outliers


# ============================================================
# PRICE JUMP CHECK
# ============================================================

def price_jump_check(df, market):

    print("\n" + "-" * 80)
    print(f"15. SUDDEN PRICE JUMP CHECK — {market}")
    print("-" * 80)

    temp = df[
        [
            "date",
            "modal_price"
        ]
    ].copy()

    temp = temp.sort_values(
        "date"
    )

    temp["previous_price"] = (
        temp["modal_price"]
        .shift(1)
    )

    temp["percentage_change"] = (
        (
            temp["modal_price"]
            -
            temp["previous_price"]
        )
        /
        temp["previous_price"]
    ) * 100

    # Absolute change greater than 50%

    jumps = temp[
        temp["percentage_change"]
        .abs()
        > 50
    ].copy()

    print(
        "Price changes greater than ±50%:",
        len(jumps)
    )

    if len(jumps) > 0:

        print(
            "\nLargest price movements:"
        )

        print(
            jumps
            .sort_values(
                "percentage_change",
                key=lambda x: x.abs(),
                ascending=False
            )
            [
                [
                    "date",
                    "previous_price",
                    "modal_price",
                    "percentage_change"
                ]
            ]
            .head(15)
            .to_string(index=False)
        )

    return jumps


# ============================================================
# RECENT OBSERVATIONS
# ============================================================

def show_recent_observations(df, market):

    print("\n" + "-" * 80)
    print(
        f"16. LATEST OBSERVATIONS — {market}"
    )
    print("-" * 80)

    print(
        df[
            [
                "date",
                "min_price",
                "modal_price",
                "max_price"
            ]
        ]
        .sort_values(
            "date",
            ascending=False
        )
        .head(10)
        .to_string(index=False)
    )


# ============================================================
# FINAL DATASET VERDICT
# ============================================================

def generate_verdict(
    df,
    market,
    missing_count,
    duplicate_dates,
    invalid_prices,
    coverage
):

    print("\n" + "-" * 80)
    print(
        f"17. VALIDATION VERDICT — {market}"
    )
    print("-" * 80)

    problems = []

    if missing_count > 0:

        problems.append(
            "missing values"
        )

    if duplicate_dates > 0:

        problems.append(
            "duplicate dates"
        )

    if invalid_prices > 0:

        problems.append(
            "invalid price relationships"
        )

    if len(df) < 1000:

        problems.append(
            "low number of observations"
        )

    if problems:

        print(
            "STATUS: NEEDS INVESTIGATION"
        )

        print(
            "Problems:",
            ", ".join(problems)
        )

    else:

        print(
            "STATUS: STRUCTURALLY VALID"
        )

        print(
            "No major structural problems detected."
        )

    print(
        f"Calendar observation ratio: "
        f"{coverage:.2f}%"
    )

    print(
        "\nIMPORTANT:"
    )

    print(
        "IQR outliers and large price jumps are NOT "
        "automatically removed."
    )

    print(
        "They must be investigated before deciding "
        "whether they are genuine market events."
    )


# ============================================================
# PROCESS ONE DATASET
# ============================================================

def validate_market(
    market,
    filename
):

    df = load_dataset(
        market,
        filename
    )

    if df is None:

        return None

    # --------------------------------------------------------
    # 1
    # --------------------------------------------------------

    valid_columns = check_required_columns(
        df,
        market
    )

    if not valid_columns:

        return None

    # --------------------------------------------------------
    # 2
    # --------------------------------------------------------

    df = validate_data_types(
        df
    )

    # --------------------------------------------------------
    # 3
    # --------------------------------------------------------

    missing_count = check_missing_values(
        df
    )

    # --------------------------------------------------------
    # 4
    # --------------------------------------------------------

    duplicate_dates = check_duplicate_dates(
        df
    )

    # --------------------------------------------------------
    # 5
    # --------------------------------------------------------

    check_date_order(
        df
    )

    # --------------------------------------------------------
    # 6
    # --------------------------------------------------------

    invalid_prices = check_price_logic(
        df
    )

    # --------------------------------------------------------
    # 7
    # --------------------------------------------------------

    price_statistics(
        df,
        market
    )

    # --------------------------------------------------------
    # 8
    # --------------------------------------------------------

    check_price_range(
        df
    )

    # --------------------------------------------------------
    # 9
    # --------------------------------------------------------

    coverage_info = date_coverage(
        df,
        market
    )

    # --------------------------------------------------------
    # 10
    # --------------------------------------------------------

    gap_analysis(
        df
    )

    # --------------------------------------------------------
    # 11
    # --------------------------------------------------------

    yearly_counts(
        df
    )

    # --------------------------------------------------------
    # 12
    # --------------------------------------------------------

    recent_data_check(
        df
    )

    # --------------------------------------------------------
    # 13
    # --------------------------------------------------------

    yearly_price_statistics(
        df
    )

    # --------------------------------------------------------
    # 14
    # --------------------------------------------------------

    outlier_check(
        df,
        market
    )

    # --------------------------------------------------------
    # 15
    # --------------------------------------------------------

    price_jump_check(
        df,
        market
    )

    # --------------------------------------------------------
    # 16
    # --------------------------------------------------------

    show_recent_observations(
        df,
        market
    )

    # --------------------------------------------------------
    # 17
    # --------------------------------------------------------

    generate_verdict(
        df,
        market,
        missing_count,
        duplicate_dates,
        invalid_prices,
        coverage_info["coverage"]
    )

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 80)
    print("MODEL DATASET VALIDATION")
    print("=" * 80)

    results = {}

    for market, filename in DATASETS.items():

        df = validate_market(
            market,
            filename
        )

        if df is not None:

            results[market] = df

    # ========================================================
    # CROSS-MARKET SUMMARY
    # ========================================================

    print("\n")
    print("=" * 80)
    print("CROSS-MARKET SUMMARY")
    print("=" * 80)

    summary = []

    for market, df in results.items():

        start = df["date"].min()
        end = df["date"].max()

        calendar_days = (
            end - start
        ).days + 1

        coverage = (
            len(df) /
            calendar_days
        ) * 100

        summary.append(
            {
                "market": market,
                "rows": len(df),
                "start_date": start.date(),
                "end_date": end.date(),
                "coverage_percent": round(
                    coverage,
                    2
                ),
                "mean_modal_price": round(
                    df["modal_price"].mean(),
                    2
                ),
                "median_modal_price": round(
                    df["modal_price"].median(),
                    2
                ),
                "min_modal_price": df[
                    "modal_price"
                ].min(),
                "max_modal_price": df[
                    "modal_price"
                ].max()
            }
        )

    summary_df = pd.DataFrame(
        summary
    )

    print(
        summary_df.to_string(
            index=False
        )
    )

    # ========================================================
    # SAVE VALIDATION SUMMARY
    # ========================================================

    output_path = os.path.join(
        PROCESSED_DIR,
        "model_dataset_validation_summary.csv"
    )

    summary_df.to_csv(
        output_path,
        index=False
    )

    print("\n")
    print(
        "Validation summary saved:"
    )

    print(
        output_path
    )

    print("\n")
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()