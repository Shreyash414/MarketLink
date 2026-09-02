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

MAX_RETRIES = 7

REQUEST_TIMEOUT = (30, 180)

OUTPUT_DIR = "data/raw"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# SELECTED MARKETS
# ============================================================

MARKETS = [
    {
        "state": "Uttar Pradesh",
        "district": "Bareilly",
        "market": "Bareilly",
        "filename": "onion_bareilly_history.csv"
    },
    {
        "state": "Odisha",
        "district": "Bargarh",
        "market": "Bargarh",
        "filename": "onion_bargarh_history.csv"
    },
    {
        "state": "Maharashtra",
        "district": "Nagpur",
        "market": "Nagpur",
        "filename": "onion_nagpur_history.csv"
    }
]


# ============================================================
# CHECK API KEY
# ============================================================

if not API_KEY:
    raise ValueError(
        "DATA_GOV_API_KEY not found.\n"
        "Make sure your .env file contains:\n"
        "DATA_GOV_API_KEY=your_key"
    )


# ============================================================
# DOWNLOAD ONE MARKET
# ============================================================

def download_market(state, district, market):

    print("\n" + "=" * 75)
    print(f"DOWNLOADING: {state} | {district} | {market}")
    print("=" * 75)

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

        records = None

        # ----------------------------------------------------
        # RETRIES
        # ----------------------------------------------------

        for attempt in range(1, MAX_RETRIES + 1):

            try:

                response = requests.get(
                    BASE_URL,
                    params=params,
                    timeout=REQUEST_TIMEOUT
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

                    data = response.json()

                    records = data.get("records", [])

                    break

                # ------------------------------------------------
                # TEMPORARY SERVER ERRORS
                # ------------------------------------------------

                elif response.status_code in [502, 503, 504]:

                    print(
                        f"Temporary server error "
                        f"({response.status_code}). "
                        f"Retrying in 10 seconds..."
                    )

                    time.sleep(10)

                # ------------------------------------------------
                # OTHER API ERRORS
                # ------------------------------------------------

                else:

                    print(
                        "API error:",
                        response.text[:500]
                    )

                    return pd.DataFrame()

            except requests.exceptions.Timeout:

                print(
                    "Request timed out. "
                    "Retrying in 10 seconds..."
                )

                time.sleep(10)

            except requests.exceptions.RequestException as e:

                print(
                    f"Request error: {e}"
                )

                print(
                    "Retrying in 10 seconds..."
                )

                time.sleep(10)

        # --------------------------------------------------------
        # ALL RETRIES FAILED
        # --------------------------------------------------------

        if records is None:

            print("\n" + "!" * 75)
            print(
                f"FAILED: {market} at offset {offset}"
            )
            print("!" * 75)

            print(
                "The API did not respond successfully "
                "after all retry attempts."
            )

            # Return what we have downloaded so far.
            # This allows us to save partial progress.
            break

        # --------------------------------------------------------
        # NO MORE RECORDS
        # --------------------------------------------------------

        if not records:

            print(
                f"No more records for {market}."
            )

            break

        # --------------------------------------------------------
        # ADD RECORDS
        # --------------------------------------------------------

        all_records.extend(records)

        print(
            f"Downloaded so far: {len(all_records)}"
        )

        # --------------------------------------------------------
        # LAST PAGE
        # --------------------------------------------------------

        if len(records) < LIMIT:

            print(
                "Last page reached."
            )

            break

        # --------------------------------------------------------
        # NEXT PAGE
        # --------------------------------------------------------

        offset += LIMIT

        # Wait before next request
        time.sleep(3)

    # ============================================================
    # CREATE DATAFRAME
    # ============================================================

    df = pd.DataFrame(all_records)

    print("\n" + "-" * 75)

    if len(df) == 0:

        print(
            f"No records downloaded for {market}."
        )

    else:

        print(
            f"Finished {market}: "
            f"{len(df)} records"
        )

    print("-" * 75)

    return df


# ============================================================
# SAVE MARKET
# ============================================================

def save_market(df, filename):

    if df.empty:

        print(
            f"Nothing to save: {filename}"
        )

        return None

    path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    df.to_csv(
        path,
        index=False
    )

    print(
        f"Saved: {path}"
    )

    print(
        f"Rows: {len(df)}"
    )

    print(
        f"Columns: {len(df.columns)}"
    )

    return path


# ============================================================
# VERIFY SAVED FILE
# ============================================================

def verify_file(path):

    if not os.path.exists(path):

        print(
            f"Verification failed: {path}"
        )

        return

    df = pd.read_csv(path)

    print(
        f"Verified: {path}"
    )

    print(
        f"Rows in file: {len(df)}"
    )

    print(
        f"Columns: {list(df.columns)}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 75)
    print("SELECTED MARKET DOWNLOADER")
    print("=" * 75)

    print(
        "\nMarkets:"
    )

    for market in MARKETS:

        print(
            f"- {market['market']} "
            f"({market['state']})"
        )

    print(
        f"\nOutput directory: {OUTPUT_DIR}"
    )

    # ========================================================
    # PROCESS EACH MARKET
    # ========================================================

    for market_info in MARKETS:

        state = market_info["state"]
        district = market_info["district"]
        market = market_info["market"]
        filename = market_info["filename"]

        output_path = os.path.join(
            OUTPUT_DIR,
            filename
        )

        # ----------------------------------------------------
        # CHECK IF FILE ALREADY EXISTS
        # ----------------------------------------------------

        if os.path.exists(output_path):

            existing_df = pd.read_csv(
                output_path
            )

            print("\n" + "=" * 75)
            print(
                f"FILE ALREADY EXISTS: {market}"
            )
            print("=" * 75)

            print(
                f"File: {output_path}"
            )

            print(
                f"Rows: {len(existing_df)}"
            )

            answer = input(
                "\nDownload this market again? "
                "(y/n): "
            ).strip().lower()

            if answer != "y":

                print(
                    f"Skipping {market}."
                )

                continue

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        df = download_market(
            state,
            district,
            market
        )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        if not df.empty:

            save_market(
                df,
                filename
            )

            # ------------------------------------------------
            # VERIFY
            # ------------------------------------------------

            verify_file(
                output_path
            )

        else:

            print(
                f"Could not download {market}."
            )

        # Wait before next market
        print(
            "\nWaiting 5 seconds before next market..."
        )

        time.sleep(5)

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n")
    print("=" * 75)
    print("DOWNLOAD SUMMARY")
    print("=" * 75)

    for market in MARKETS:

        path = os.path.join(
            OUTPUT_DIR,
            market["filename"]
        )

        if os.path.exists(path):

            df = pd.read_csv(path)

            print(
                f"{market['market']:15s} "
                f"{len(df):8d} records "
                f"-> {path}"
            )

        else:

            print(
                f"{market['market']:15s} "
                f"NOT DOWNLOADED"
            )

    print("\n")
    print("=" * 75)
    print("DOWNLOAD PROCESS COMPLETE")
    print("=" * 75)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()