import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

# --------------------------------------------------
# 1. Load API key
# --------------------------------------------------

load_dotenv()

API_KEY = os.getenv("DATA_GOV_API_KEY")

if not API_KEY:
    raise ValueError("API key not found in .env file")


# --------------------------------------------------
# 2. API information
# --------------------------------------------------

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"

URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


# --------------------------------------------------
# 3. API settings
# --------------------------------------------------

LIMIT = 1000

offset = 0

all_records = []


# --------------------------------------------------
# 4. Headers
# --------------------------------------------------

headers = {
    "User-Agent": "Mozilla/5.0"
}


# --------------------------------------------------
# 5. Download data
# --------------------------------------------------

while True:

    print()
    print("----------------------------------------")
    print(f"Requesting records from offset {offset}")
    print("----------------------------------------")

    params = {
        "api-key": API_KEY,
        "format": "json",
        "offset": offset,
        "limit": LIMIT
    }

    # ----------------------------------------------
    # Retry mechanism
    # ----------------------------------------------

    success = False

    for attempt in range(1, 6):

        try:

            print(f"Attempt {attempt}/5")

            response = requests.get(
                URL,
                params=params,
                headers=headers,
                timeout=(10, 90)
            )

            print("Status code:", response.status_code)

            if response.status_code == 200:
                success = True
                break

            print("Server returned:", response.status_code)

        except requests.exceptions.RequestException as e:

            print("Request error:", e)

        # Wait before retrying
        wait_time = 2 ** attempt

        print(f"Waiting {wait_time} seconds...")

        time.sleep(wait_time)


    # ----------------------------------------------
    # Stop if all attempts failed
    # ----------------------------------------------

    if not success:

        print()
        print("ERROR: Failed after 5 attempts.")
        print("Stopping downloader.")

        break


    # --------------------------------------------------
    # 6. Convert response to JSON
    # --------------------------------------------------

    data = response.json()

    records = data.get("records", [])

    print("Records received:", len(records))


    # --------------------------------------------------
    # 7. Stop if no records
    # --------------------------------------------------

    if not records:

        print("No more records available.")
        break


    # --------------------------------------------------
    # 8. Add records to our list
    # --------------------------------------------------

    all_records.extend(records)

    print("Total downloaded:", len(all_records))


    # --------------------------------------------------
    # 9. Check whether we reached the end
    # --------------------------------------------------

    if len(records) < LIMIT:

        print()
        print("Last page reached.")
        break


    # --------------------------------------------------
    # 10. Move to next page
    # --------------------------------------------------

    offset += LIMIT

    # Small delay to avoid hitting the API too quickly
    time.sleep(2)


# --------------------------------------------------
# 11. Convert everything to DataFrame
# --------------------------------------------------

print()
print("Creating DataFrame...")

df = pd.DataFrame(all_records)


# --------------------------------------------------
# 12. Display information
# --------------------------------------------------

print()
print("========================================")
print("DOWNLOAD COMPLETE")
print("========================================")

print("Total rows:", len(df))

print("Columns:")
print(df.columns.tolist())


# --------------------------------------------------
# 13. Save CSV
# --------------------------------------------------

output_file = "data/raw/mandi_current_raw.csv"

df.to_csv(
    output_file,
    index=False
)

print()
print("Saved successfully!")
print("File:", output_file)