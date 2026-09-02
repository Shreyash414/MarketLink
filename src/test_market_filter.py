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
# 3. Filters
# -----------------------------------------

params = {
    "api-key": API_KEY,
    "format": "json",
    "offset": 0,
    "limit": 10,

    "filters[Commodity]": "Onion",
    "filters[State]": "Punjab",
    "filters[Market]": "Bhawanigarh"
}


# -----------------------------------------
# 4. Headers
# -----------------------------------------

headers = {
    "User-Agent": "Mozilla/5.0"
}


# -----------------------------------------
# 5. Request
# -----------------------------------------

try:

    print("Requesting Onion + Bhawanigarh data...")

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
    # 6. Information
    # -----------------------------------------

    print("\nAPI status:", data.get("status"))

    print(
        "Total matching records:",
        data.get("total")
    )


    # -----------------------------------------
    # 7. Records
    # -----------------------------------------

    records = data.get("records", [])

    print(
        "Records received:",
        len(records)
    )


    # -----------------------------------------
    # 8. Display records
    # -----------------------------------------

    print("\nRecords:")

    for record in records:

        print(
            record.get("Arrival_Date"),
            "|",
            record.get("State"),
            "|",
            record.get("Market"),
            "| Modal:",
            record.get("Modal_Price")
        )


except requests.exceptions.Timeout:

    print("\nERROR: Request timed out.")


except requests.exceptions.RequestException as e:

    print("\nERROR: Request failed.")
    print(e)


except Exception as e:

    print("\nERROR:", e)