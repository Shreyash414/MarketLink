import os
import requests
from dotenv import load_dotenv

# -----------------------------------------
# 1. Load API key
# -----------------------------------------

load_dotenv()

API_KEY = os.getenv("DATA_GOV_API_KEY")

if not API_KEY:
    print("ERROR: API key not found")
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
    "limit": 10000,

    # We only want Onion
    "filters[Commodity]": "Onion"
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

    print("Requesting Onion market data...")

    response = requests.get(
        URL,
        params=params,
        headers=headers,
        timeout=(10, 120)
    )

    print("Status code:", response.status_code)

    response.raise_for_status()

    data = response.json()


    # -----------------------------------------
    # 6. API information
    # -----------------------------------------

    print("\nAPI status:", data.get("status"))

    print(
        "Total Onion records:",
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
    # 8. Find unique markets
    # -----------------------------------------

    markets = {}

    for record in records:

        state = record.get("State")
        district = record.get("District")
        market = record.get("Market")

        key = (
            state,
            district,
            market
        )

        markets[key] = markets.get(key, 0) + 1


    # -----------------------------------------
    # 9. Display markets
    # -----------------------------------------

    print("\nUnique markets in this sample:")

    print(
        "Number of markets:",
        len(markets)
    )

    print("\nTop markets in this sample:")

    sorted_markets = sorted(
        markets.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for market, count in sorted_markets[:50]:

        state, district, market_name = market

        print(
            f"{state} | "
            f"{district} | "
            f"{market_name} | "
            f"Records: {count}"
        )


    print("\n===================================")
    print("Market analysis completed")
    print("===================================")


except requests.exceptions.Timeout:

    print("\nERROR: Request timed out.")


except requests.exceptions.RequestException as e:

    print("\nERROR: Request failed.")

    print(e)


except Exception as e:

    print("\nERROR:")

    print(e)