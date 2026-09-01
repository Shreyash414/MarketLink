import os
import requests
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
# 2. Historical resource
# -----------------------------------------

RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"

URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


# -----------------------------------------
# 3. Request parameters
# -----------------------------------------

params = {
    "api-key": API_KEY,
    "format": "json",
    "offset": 0,
    "limit": 10
}


# -----------------------------------------
# 4. Headers
# -----------------------------------------

headers = {
    "User-Agent": "Mozilla/5.0"
}


# -----------------------------------------
# 5. Send request
# -----------------------------------------

try:

    print("Requesting historical market data...")

    response = requests.get(
        URL,
        params=params,
        headers=headers,
        timeout=(10, 90)
    )

    print("Status code:", response.status_code)

    response.raise_for_status()

    data = response.json()


    # -----------------------------------------
    # 6. Basic API information
    # -----------------------------------------

    print("\nAPI status:", data.get("status"))

    print(
        "Total records:",
        data.get("total")
    )


    # -----------------------------------------
    # 7. Get records
    # -----------------------------------------

    records = data.get("records", [])

    print(
        "Records received:",
        len(records)
    )


    # -----------------------------------------
    # 8. Check records
    # -----------------------------------------

    if not records:

        print("\nNo records received.")

        exit()


    # -----------------------------------------
    # 9. Show first record
    # -----------------------------------------

    print("\nFirst record:")

    print(records[0])


    # -----------------------------------------
    # 10. Show column names
    # -----------------------------------------

    print("\nColumns:")

    for column in records[0].keys():

        print(column)


    # -----------------------------------------
    # 11. Show dates
    # -----------------------------------------

    print("\nDates in this batch:")

    for record in records:

        print(
            record.get("Arrival_Date")
        )


    # -----------------------------------------
    # 12. Show commodities
    # -----------------------------------------

    print("\nCommodities in this batch:")

    for record in records:

        print(
            record.get("Commodity")
        )


    # -----------------------------------------
    # 13. Show markets
    # -----------------------------------------

    print("\nMarkets in this batch:")

    for record in records:

        print(
            record.get("Market")
        )


    print("\n===================================")
    print("Historical API test completed")
    print("===================================")


except requests.exceptions.Timeout:

    print("\nERROR: API request timed out.")


except requests.exceptions.RequestException as e:

    print("\nERROR: API request failed.")

    print(e)


except Exception as e:

    print("\nERROR:")

    print(e)