import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

API_KEY = os.getenv("DATA_GOV_API_KEY")

RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"

BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

LIMIT = 1000

OUTPUT_DIR = "data/processed/market_profiles"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# SELECTED MARKETS
# ============================================================

MARKETS = [
    {
        "state": "Uttar Pradesh",
        "district": "Bareilly",
        "market": "Bareilly"
    },
    {
        "state": "Odisha",
        "district": "Bargarh",
        "market": "Bargarh"
    },
    {
        "state": "Maharashtra",
        "district": "Nagpur",
        "market": "Nagpur"
    }
]


# ============================================================
# CHECK API KEY
# ============================================================

if not API_KEY:
    raise ValueError(
        "DATA_GOV_API_KEY not found. "
        "Make sure it is present in your .env file."
    )


# ============================================================
# DOWNLOAD MARKET DATA
# ============================================================

def download_market(state, district, market):

    print("\n" + "=" * 70)
    print(f"DOWNLOADING: {state} | {district} | {market}")
    print("=" * 70)

    all_records = []
    offset = 0

    while True:

        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": LIMIT,
            "offset": offset,
            "filters[State]": state,
            "filters[District]": district,
            "filters[Market]": market,
            "filters[Commodity]": "Onion"
        }

        success = False

        for attempt in range(1, 6):

            try:

                response = requests.get(
                    BASE_URL,
                    params=params,
                    timeout=(30, 180)
)

                print(
                    f"{market} | offset={offset} | "
                    f"attempt={attempt} | "
                    f"status={response.status_code}"
                )

                if response.status_code == 200:

                    data = response.json()

                    records = data.get("records", [])

                    if not records:
                        success = True
                        break

                    all_records.extend(records)

                    print(
                        f"Downloaded: {len(all_records)}"
                    )

                    success = True
                    break

                elif response.status_code in [502, 503, 504]:

                    print("Temporary server error. Retrying...")
                    time.sleep(5)

                else:

                    print(
                        "API Error:",
                        response.text[:300]
                    )

                    return pd.DataFrame()

            except requests.exceptions.RequestException as e:

                print(
                    f"Request error: {e}"
                )

                time.sleep(5)

        if not success:
            print(
                f"Failed after 5 attempts at offset {offset}"
            )
            break

        if not records:
            break

        if len(records) < LIMIT:
            break

        offset += LIMIT

        # Small delay to avoid hitting API too aggressively
        time.sleep(2)

    df = pd.DataFrame(all_records)

    print(
        f"\nFinished {market}: "
        f"{len(df)} records"
    )

    return df


# ============================================================
# BASIC INFORMATION
# ============================================================

def basic_information(df, market):

    print("\n" + "-" * 70)
    print(f"BASIC INFORMATION — {market}")
    print("-" * 70)

    print("Total records:", len(df))

    if df.empty:
        return

    if "Arrival_Date" in df.columns:

        dates = pd.to_datetime(
            df["Arrival_Date"],
            dayfirst=True,
            errors="coerce"
        )

        print("Unique dates:", dates.nunique())

        print(
            "Start date:",
            dates.min().strftime("%Y-%m-%d")
            if pd.notna(dates.min())
            else "N/A"
        )

        print(
            "End date:",
            dates.max().strftime("%Y-%m-%d")
            if pd.notna(dates.max())
            else "N/A"
        )


# ============================================================
# VARIETY ANALYSIS
# ============================================================

def analyze_varieties(df, market):

    print("\n" + "-" * 70)
    print(f"VARIETY DISTRIBUTION — {market}")
    print("-" * 70)

    if "Variety" not in df.columns:

        print("Variety column not found.")
        return

    variety_counts = (
        df["Variety"]
        .fillna("MISSING")
        .value_counts()
    )

    print(variety_counts.to_string())

    print("\nDetailed variety information:")

    for variety, count in variety_counts.items():

        subset = df[
            df["Variety"].fillna("MISSING") == variety
        ]

        if "Arrival_Date" in subset.columns:

            dates = pd.to_datetime(
                subset["Arrival_Date"],
                dayfirst=True,
                errors="coerce"
            )

            unique_dates = dates.nunique()

        else:

            unique_dates = "N/A"

        print(
            f"{str(variety):30s} "
            f"Records={count:6d} "
            f"Unique Dates={str(unique_dates):6s}"
        )


# ============================================================
# GRADE ANALYSIS
# ============================================================

def analyze_grades(df, market):

    print("\n" + "-" * 70)
    print(f"GRADE DISTRIBUTION — {market}")
    print("-" * 70)

    if "Grade" not in df.columns:

        print("Grade column not found.")
        return

    grade_counts = (
        df["Grade"]
        .fillna("MISSING")
        .value_counts()
    )

    print(grade_counts.to_string())


# ============================================================
# PRICE VALIDATION
# ============================================================

def validate_prices(df, market):

    print("\n" + "-" * 70)
    print(f"PRICE VALIDATION — {market}")
    print("-" * 70)

    required_columns = [
        "Min_Price",
        "Modal_Price",
        "Max_Price"
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:

        print(
            "Missing price columns:",
            missing_columns
        )

        return

    price_df = df.copy()

    for col in required_columns:

        price_df[col] = pd.to_numeric(
            price_df[col],
            errors="coerce"
        )

    missing_prices = (
        price_df[required_columns]
        .isna()
        .any(axis=1)
        .sum()
    )

    invalid_min_modal = (
        price_df["Min_Price"] >
        price_df["Modal_Price"]
    ).sum()

    invalid_modal_max = (
        price_df["Modal_Price"] >
        price_df["Max_Price"]
    ).sum()

    invalid_min_max = (
        price_df["Min_Price"] >
        price_df["Max_Price"]
    ).sum()

    negative_prices = (
        (price_df[required_columns] < 0)
        .any(axis=1)
        .sum()
    )

    print("Missing price records:", missing_prices)

    print(
        "Min > Modal:",
        invalid_min_modal
    )

    print(
        "Modal > Max:",
        invalid_modal_max
    )

    print(
        "Min > Max:",
        invalid_min_max
    )

    print(
        "Negative price records:",
        negative_prices
    )

    total_invalid = (
        price_df["Min_Price"].gt(
            price_df["Modal_Price"]
        )
        |
        price_df["Modal_Price"].gt(
            price_df["Max_Price"]
        )
        |
        price_df["Min_Price"].gt(
            price_df["Max_Price"]
        )
        |
        (price_df[required_columns] < 0).any(axis=1)
    ).sum()

    print(
        "Total logically invalid records:",
        total_invalid
    )


# ============================================================
# DUPLICATE ANALYSIS
# ============================================================

def analyze_duplicates(df, market):

    print("\n" + "-" * 70)
    print(f"DUPLICATE ANALYSIS — {market}")
    print("-" * 70)

    exact_duplicates = df.duplicated().sum()

    print(
        "Exact duplicate rows:",
        exact_duplicates
    )

    business_columns = [
        "Arrival_Date",
        "Commodity",
        "State",
        "District",
        "Market",
        "Variety",
        "Grade"
    ]

    available_columns = [
        col
        for col in business_columns
        if col in df.columns
    ]

    if available_columns:

        business_duplicates = df.duplicated(
            subset=available_columns
        ).sum()

        print(
            "Business-key duplicate rows:",
            business_duplicates
        )

        print(
            "Duplicate key:",
            available_columns
        )


# ============================================================
# YEARLY ANALYSIS
# ============================================================

def analyze_yearly_data(df, market):

    print("\n" + "-" * 70)
    print(f"YEARLY RECORDS — {market}")
    print("-" * 70)

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

    print(yearly.to_string())

    print("\nRecent years:")

    for year in range(2021, 2026):

        count = yearly.get(year, 0)

        print(
            f"{year}: {count}"
        )


# ============================================================
# SAVE VARIETY SUMMARY
# ============================================================

def save_variety_summary(df, market):

    if "Variety" not in df.columns:
        return

    summary = (
        df.groupby(
            ["Variety"],
            dropna=False
        )
        .agg(
            records=("Variety", "size"),
            unique_dates=("Arrival_Date", "nunique")
        )
        .reset_index()
    )

    filename = (
        market.lower()
        .replace(" ", "_")
        + "_variety_summary.csv"
    )

    path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    summary.to_csv(
        path,
        index=False
    )

    print(
        f"\nSaved variety summary: {path}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 75)
    print("SELECTED MARKET PROFILING")
    print("=" * 75)

    all_summaries = []

    for market_info in MARKETS:

        state = market_info["state"]
        district = market_info["district"]
        market = market_info["market"]

        df = download_market(
            state,
            district,
            market
        )

        if df.empty:

            print(
                f"No data available for {market}"
            )

            continue

        # ----------------------------------------------------
        # Basic information
        # ----------------------------------------------------

        basic_information(
            df,
            market
        )

        # ----------------------------------------------------
        # Variety
        # ----------------------------------------------------

        analyze_varieties(
            df,
            market
        )

        # ----------------------------------------------------
        # Grade
        # ----------------------------------------------------

        analyze_grades(
            df,
            market
        )

        # ----------------------------------------------------
        # Prices
        # ----------------------------------------------------

        validate_prices(
            df,
            market
        )

        # ----------------------------------------------------
        # Duplicates
        # ----------------------------------------------------

        analyze_duplicates(
            df,
            market
        )

        # ----------------------------------------------------
        # Yearly records
        # ----------------------------------------------------

        analyze_yearly_data(
            df,
            market
        )

        # ----------------------------------------------------
        # Save raw downloaded market data
        # ----------------------------------------------------

        filename = (
            market.lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("&", "and")
            + "_onion_history.csv"
        )

        path = os.path.join(
            OUTPUT_DIR,
            filename
        )

        df.to_csv(
            path,
            index=False
        )

        print(
            f"\nSaved market data: {path}"
        )

        # ----------------------------------------------------
        # Save variety summary
        # ----------------------------------------------------

        save_variety_summary(
            df,
            market
        )

        # ----------------------------------------------------
        # Overall summary
        # ----------------------------------------------------

        if "Arrival_Date" in df.columns:

            dates = pd.to_datetime(
                df["Arrival_Date"],
                dayfirst=True,
                errors="coerce"
            )

            unique_dates = dates.nunique()

            start_date = dates.min()

            end_date = dates.max()

        else:

            unique_dates = None
            start_date = None
            end_date = None

        recent_records = 0

        if "Arrival_Date" in df.columns:

            recent_records = (
                dates.dt.year
                .between(2021, 2025)
                .sum()
            )

        all_summaries.append(
            {
                "state": state,
                "district": district,
                "market": market,
                "records": len(df),
                "unique_dates": unique_dates,
                "start_date": start_date,
                "end_date": end_date,
                "recent_records_2021_2025": recent_records
            }
        )

        # Wait before next market
        time.sleep(5)

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n")
    print("=" * 100)
    print("FINAL SELECTED MARKET SUMMARY")
    print("=" * 100)

    summary_df = pd.DataFrame(
        all_summaries
    )

    if not summary_df.empty:

        print(
            summary_df.to_string(
                index=False
            )
        )

        summary_path = os.path.join(
            OUTPUT_DIR,
            "selected_markets_summary.csv"
        )

        summary_df.to_csv(
            summary_path,
            index=False
        )

        print(
            f"\nSaved final summary: {summary_path}"
        )

    print("\n")
    print("=" * 75)
    print("PROFILING COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()