import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

# -----------------------------------------
# 1. Load API key
# -----------------------------------------

load_dotenv()

API_KEY = os.getenv("DATA_GOV_API_KEY")

if not API_KEY:
    print("ERROR: API key not found in .env")
    exit()


# -----------------------------------------
# 2. API information
# -----------------------------------------

RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"

URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


# -----------------------------------------
# 3. Filters
# -----------------------------------------

COMMODITY = "Onion"
STATE = "Punjab"
MARKET = "Bhawanigarh"


# -----------------------------------------
# 4. Download settings
# -----------------------------------------

LIMIT = 1000

offset = 0

all_records = []


# -----------------------------------------
# 5. Headers
# -----------------------------------------

headers = {
    "User-Agent": "Mozilla/5.0"
}


# -----------------------------------------
# 6. Download pages
# -----------------------------------------

while True:

    print()
    print("=" * 50)
    print(f"Requesting offset: {offset}")
    print("=" * 50)

    params = {
        "api-key": API_KEY,
        "format": "json",
        "offset": offset,
        "limit": LIMIT,

        "filters[Commodity]": COMMODITY,
        "filters[State]": STATE,
        "filters[Market]": MARKET
    }

    success = False

    # -----------------------------------------
    # Retry up to 5 times
    # -----------------------------------------

    for attempt in range(1, 6):

        try:

            print(f"Attempt {attempt}/5")

            response = requests.get(
                URL,
                params=params,
                headers=headers,
                timeout=(10, 90)
            )

            print(
                "Status code:",
                response.status_code
            )

            if response.status_code == 200:

                success = True
                break

            print(
                "Server returned:",
                response.status_code
            )

        except requests.exceptions.RequestException as e:

            print("Request error:", e)

        wait_time = 2 ** attempt

        print(
            f"Waiting {wait_time} seconds..."
        )

        time.sleep(wait_time)


    # -----------------------------------------
    # Stop if request failed
    # -----------------------------------------

    if not success:

        print()
        print("ERROR: Failed after 5 attempts.")
        print("Stopping.")

        break


    # -----------------------------------------
    # Convert JSON
    # -----------------------------------------

    data = response.json()

    records = data.get("records", [])

    total_records = data.get("total", 0)

    print(
        "Total matching records:",
        total_records
    )

    print(
        "Records received:",
        len(records)
    )


    # -----------------------------------------
    # Stop if no records
    # -----------------------------------------

    if not records:

        print("No more records.")
        break


    # -----------------------------------------
    # Add records
    # -----------------------------------------

    all_records.extend(records)

    print(
        "Total downloaded:",
        len(all_records)
    )


    # -----------------------------------------
    # Check final page
    # -----------------------------------------

    if len(records) < LIMIT:

        print()
        print("Last page reached.")
        break


    offset += LIMIT

    time.sleep(2)


# -----------------------------------------
# 7. Create DataFrame
# -----------------------------------------

print()
print("Creating DataFrame...")

df = pd.DataFrame(all_records)


# -----------------------------------------
# 8. Convert columns
# -----------------------------------------

df["Arrival_Date"] = pd.to_datetime(
    df["Arrival_Date"],
    dayfirst=True,
    errors="coerce"
)

df["Min_Price"] = pd.to_numeric(
    df["Min_Price"],
    errors="coerce"
)

df["Max_Price"] = pd.to_numeric(
    df["Max_Price"],
    errors="coerce"
)

df["Modal_Price"] = pd.to_numeric(
    df["Modal_Price"],
    errors="coerce"
)


# -----------------------------------------
# 9. Sort by date
# -----------------------------------------

df = df.sort_values(
    "Arrival_Date"
).reset_index(drop=True)


# -----------------------------------------
# 10. Display summary
# -----------------------------------------

print()
print("=" * 50)
print("DOWNLOAD COMPLETE")
print("=" * 50)

print("Total rows:", len(df))

print(
    "Earliest date:",
    df["Arrival_Date"].min()
)

print(
    "Latest date:",
    df["Arrival_Date"].max()
)

print(
    "Unique dates:",
    df["Arrival_Date"].nunique()
)


# -----------------------------------------
# 11. Records per year
# -----------------------------------------

print()
print("Records per year:")

print(
    df["Arrival_Date"]
    .dt.year
    .value_counts()
    .sort_index()
)


# -----------------------------------------
# 12. Missing values
# -----------------------------------------

print()
print("Missing values:")

print(df.isnull().sum())


# -----------------------------------------
# 13. Duplicate rows
# -----------------------------------------

print()
print(
    "Duplicate rows:",
    df.duplicated().sum()
)


# -----------------------------------------
# 14. Price statistics
# -----------------------------------------

print()
print("Price statistics:")

print(
    df[
        [
            "Min_Price",
            "Max_Price",
            "Modal_Price"
        ]
    ].describe()
)


# -----------------------------------------
# 15. Save
# -----------------------------------------

output_file = (
    "data/raw/"
    "onion_bhawanigarh_history.csv"
)

df.to_csv(
    output_file,
    index=False
)

print()
print(
    "Saved successfully:"
)

print(output_file)