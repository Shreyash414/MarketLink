import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv


# ============================================================
# 1. LOAD API KEY
# ============================================================

load_dotenv()

API_KEY = os.getenv("DATA_GOV_API_KEY")

if not API_KEY:
    print("ERROR: API key not found")
    exit()


# ============================================================
# 2. API CONFIGURATION
# ============================================================

RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"

URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

LIMIT = 1000

MAX_RETRIES = 7

OUTPUT_DIR = "data/raw"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# 3. SELECTED MARKETS
# ============================================================

candidates = [
    ("Maharashtra", "Nagpur", "Nagpur"),
    ("Uttar Pradesh", "Bareilly", "Bareilly"),
    ("Odisha", "Bargarh", "Bargarh")
]


# ============================================================
# 4. SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0"
})


# ============================================================
# 5. FILE NAME
# ============================================================

def get_filename(market):

    filename = (
        market.lower()
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("&", "and")
    )

    return f"onion_{filename}_history.csv"


# ============================================================
# 6. DOWNLOAD ONE MARKET
# ============================================================

def download_market(state, district, market):

    records = []

    offset = 0

    while True:

        params = {
            "api-key": API_KEY,
            "format": "json",
            "offset": offset,
            "limit": LIMIT,

            "filters[Commodity]": "Onion",
            "filters[State]": state,
            "filters[District]": district,
            "filters[Market]": market
        }

        success = False

        # ----------------------------------------------------
        # RETRIES
        # ----------------------------------------------------

        for attempt in range(1, MAX_RETRIES + 1):

            try:

                response = session.get(
                    URL,
                    params=params,
                    timeout=(15, 120)
                )

                print(
                    f"{market} | "
                    f"offset={offset} | "
                    f"attempt={attempt} | "
                    f"status={response.status_code}"
                )

                # ------------------------------------------------
                # SUCCESS
                # ------------------------------------------------

                if response.status_code == 200:

                    success = True

                    break

                # ------------------------------------------------
                # TEMPORARY SERVER ERRORS
                # ------------------------------------------------

                elif response.status_code in [502, 503, 504]:

                    wait_time = attempt * 5

                    print(
                        f"Temporary server error "
                        f"{response.status_code}. "
                        f"Waiting {wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                # ------------------------------------------------
                # OTHER ERROR
                # ------------------------------------------------

                else:

                    print(
                        "Unexpected status:",
                        response.status_code
                    )

                    return records, False

            except requests.exceptions.Timeout:

                wait_time = attempt * 5

                print(
                    f"Request timed out. "
                    f"Waiting {wait_time} seconds..."
                )

                time.sleep(wait_time)

            except requests.exceptions.RequestException as e:

                wait_time = attempt * 5

                print(
                    "Request error:",
                    e
                )

                print(
                    f"Waiting {wait_time} seconds..."
                )

                time.sleep(wait_time)

        # ----------------------------------------------------
        # FAILED AFTER ALL RETRIES
        # ----------------------------------------------------

        if not success:

            print()
            print("!" * 70)

            print(
                f"FAILED: {market} "
                f"at offset {offset}"
            )

            print(
                f"Records downloaded before failure: "
                f"{len(records)}"
            )

            print("!" * 70)

            return records, False

        # ----------------------------------------------------
        # READ JSON
        # ----------------------------------------------------

        try:

            data = response.json()

        except ValueError:

            print(
                "Invalid JSON response."
            )

            return records, False

        batch = data.get(
            "records",
            []
        )

        # ----------------------------------------------------
        # NO MORE DATA
        # ----------------------------------------------------

        if not batch:

            print(
                "No more records."
            )

            return records, True

        # ----------------------------------------------------
        # ADD DATA
        # ----------------------------------------------------

        records.extend(batch)

        print(
            f"Downloaded: {len(records)}"
        )

        # ----------------------------------------------------
        # LAST PAGE
        # ----------------------------------------------------

        if len(batch) < LIMIT:

            print(
                "Last page reached."
            )

            return records, True

        # ----------------------------------------------------
        # NEXT PAGE
        # ----------------------------------------------------

        offset += LIMIT

        time.sleep(2)


# ============================================================
# 7. ANALYZE MARKET
# ============================================================

def analyze_market(
    state,
    district,
    market,
    records
):

    if not records:

        return None

    df = pd.DataFrame(records)

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    df["Arrival_Date"] = pd.to_datetime(
        df["Arrival_Date"],
        dayfirst=True,
        errors="coerce"
    )

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    for column in [
        "Min_Price",
        "Modal_Price",
        "Max_Price"
    ]:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # --------------------------------------------------------
    # REMOVE EXACT DUPLICATES
    # --------------------------------------------------------

    df = df.drop_duplicates()

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    df = df.sort_values(
        "Arrival_Date"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # DATE RANGE
    # --------------------------------------------------------

    start = df["Arrival_Date"].min()

    end = df["Arrival_Date"].max()

    # --------------------------------------------------------
    # UNIQUE DATES
    # --------------------------------------------------------

    unique_dates = (
        df["Arrival_Date"].nunique()
    )

    # --------------------------------------------------------
    # DATE GAPS
    # --------------------------------------------------------

    gaps = (
        df["Arrival_Date"]
        .diff()
        .dt.days
        .dropna()
    )

    if len(gaps) > 0:

        max_gap = int(gaps.max())

    else:

        max_gap = 0

    # --------------------------------------------------------
    # CALENDAR DAYS
    # --------------------------------------------------------

    calendar_days = (
        end - start
    ).days + 1

    # --------------------------------------------------------
    # MISSING %
    # --------------------------------------------------------

    missing_percentage = (
        (
            calendar_days
            - unique_dates
        )
        / calendar_days
    ) * 100

    # --------------------------------------------------------
    # RECENT DATA
    # --------------------------------------------------------

    recent_start = pd.Timestamp(
        "2021-01-01"
    )

    recent_records = len(
        df[
            df["Arrival_Date"]
            >= recent_start
        ]
    )

    # --------------------------------------------------------
    # RETURN RESULT
    # --------------------------------------------------------

    return {
        "state": state,
        "district": district,
        "market": market,
        "records": len(df),
        "unique_dates": unique_dates,
        "start_date": start.date(),
        "end_date": end.date(),
        "calendar_days": calendar_days,
        "missing_percentage": round(
            missing_percentage,
            2
        ),
        "max_gap_days": max_gap,
        "recent_records_2021_2025": recent_records
    }


# ============================================================
# 8. MAIN
# ============================================================

results = []


for state, district, market in candidates:

    print()
    print("=" * 70)

    print(
        f"PROCESSING: "
        f"{state} | {district} | {market}"
    )

    print("=" * 70)

    filename = get_filename(market)

    output_path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    # ========================================================
    # CHECK IF FILE ALREADY EXISTS
    # ========================================================

    if os.path.exists(output_path):

        print(
            f"Existing file found: "
            f"{output_path}"
        )

        existing_df = pd.read_csv(
            output_path
        )

        print(
            f"Existing records: "
            f"{len(existing_df)}"
        )

        answer = input(
            "Use existing file? (y/n): "
        ).strip().lower()

        if answer == "y":

            df_existing = existing_df

            # Convert back to records
            records = df_existing.to_dict(
                orient="records"
            )

            result = analyze_market(
                state,
                district,
                market,
                records
            )

            if result:

                results.append(result)

            continue

    # ========================================================
    # DOWNLOAD
    # ========================================================

    records, completed = download_market(
        state,
        district,
        market
    )

    print()
    print(
        f"Downloaded {len(records)} records "
        f"for {market}"
    )

    # ========================================================
    # SAVE EVEN IF PARTIAL
    # ========================================================

    if records:

        df = pd.DataFrame(records)

        df.to_csv(
            output_path,
            index=False
        )

        print(
            f"Saved: {output_path}"
        )

        print(
            f"Rows saved: {len(df)}"
        )

    else:

        print(
            f"No data available for {market}"
        )

        continue

    # ========================================================
    # ANALYZE
    # ========================================================

    result = analyze_market(
        state,
        district,
        market,
        records
    )

    if result:

        results.append(result)

    # ========================================================
    # STATUS
    # ========================================================

    if completed:

        print(
            f"{market} DOWNLOAD COMPLETE"
        )

    else:

        print(
            f"{market} DOWNLOAD PARTIAL"
        )

    # Wait before next market
    time.sleep(5)


# ============================================================
# 9. CREATE COMPARISON TABLE
# ============================================================

df_results = pd.DataFrame(
    results
)


if not df_results.empty:

    df_results = df_results.sort_values(
        "records",
        ascending=False
    )


# ============================================================
# 10. DISPLAY
# ============================================================

print()
print("=" * 100)
print("SELECTED MARKET QUALITY COMPARISON")
print("=" * 100)

if not df_results.empty:

    print(
        df_results.to_string(
            index=False
        )
    )

else:

    print(
        "No market data available."
    )


# ============================================================
# 11. SAVE QUALITY REPORT
# ============================================================

output_file = (
    "data/processed/"
    "selected_market_quality.csv"
)

df_results.to_csv(
    output_file,
    index=False
)

print()
print("Saved:")
print(output_file)

print()
print("=" * 75)
print("PROCESS COMPLETE")
print("=" * 75)