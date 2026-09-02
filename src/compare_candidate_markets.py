import os
import requests
import pandas as pd
import time
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
# 2. API
# -----------------------------------------

RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"

URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


# -----------------------------------------
# 3. Candidate markets
# -----------------------------------------

candidates = [
    ("Maharashtra", "Nagpur", "Nagpur"),
    ("NCT of Delhi", "Delhi", "Azadpur"),
    ("Telangana", "Hyderabad", "Bowenpally"),
    ("Punjab", "Sangrur", "Sunam"),
    ("Odisha", "Bargarh", "Bargarh"),
    ("Punjab", "Sangrur", "Khanauri"),
    ("Uttar Pradesh", "Bareilly", "Bareilly"),
    ("Rajasthan", "Jodhpur", "Jodhpur (F&V)"),
    ("Haryana", "Yamuna Nagar", "Chhachrauli"),
    ("Gujarat", "Surat", "Mahuva"),
    ("Uttar Pradesh", "Bulandshahar", "Jahangirabad"),
    ("Odisha", "Keonjhar", "Keonjhar"),
    ("Uttar Pradesh", "Bijnor", "Bijnaur"),
    ("Haryana", "Yamuna Nagar", "Jagadhri"),
    ("Haryana", "Hissar", "Narnaund"),
    ("Punjab", "Sangrur", "Bhawanigarh"),
    ("Uttar Pradesh", "Bareilly", "Bahedi"),
    ("Maharashtra", "Jalgaon", "Jalgaon"),
    ("Haryana", "Yamuna Nagar", "Sadhaura"),
    ("Madhya Pradesh", "Indore", "Indore(F&V)"),
    ("Madhya Pradesh", "Ratlam", "Ratlam"),
    ("Rajasthan", "Kota", "Kota (F&V)")
]


# -----------------------------------------
# 4. Session
# -----------------------------------------

session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0"
})


# -----------------------------------------
# 5. Function to query one market
# -----------------------------------------

def get_market_data(state, district, market):

    params = {
        "api-key": API_KEY,
        "format": "json",
        "offset": 0,
        "limit": 1,

        "filters[Commodity]": "Onion",
        "filters[State]": state,
        "filters[District]": district,
        "filters[Market]": market
    }

    for attempt in range(1, 6):

        try:

            print(
                f"Attempt {attempt}/5"
            )

            response = session.get(
                URL,
                params=params,
                timeout=(15, 120)
            )

            print(
                "Status:",
                response.status_code
            )

            # -----------------------------
            # Success
            # -----------------------------

            if response.status_code == 200:

                data = response.json()

                records = data.get(
                    "records",
                    []
                )

                return {
                    "status": "success",
                    "records": data.get(
                        "total",
                        0
                    ),
                    "sample_date": (
                        records[0].get(
                            "Arrival_Date"
                        )
                        if records
                        else None
                    )
                }


            # -----------------------------
            # Server error
            # -----------------------------

            elif response.status_code in [
                502,
                503,
                504
            ]:

                wait = attempt * 5

                print(
                    f"Server error. "
                    f"Waiting {wait} seconds..."
                )

                time.sleep(wait)

            else:

                print(
                    "Unexpected status:",
                    response.status_code
                )

                return {
                    "status": "failed",
                    "records": None,
                    "sample_date": None
                }


        except requests.exceptions.Timeout:

            print(
                "Request timed out."
            )

            wait = attempt * 5

            time.sleep(wait)


        except requests.exceptions.RequestException as e:

            print(
                "Request error:",
                e
            )

            wait = attempt * 5

            time.sleep(wait)


        except Exception as e:

            print(
                "Unexpected error:",
                e
            )

            return {
                "status": "failed",
                "records": None,
                "sample_date": None
            }


    # -----------------------------------------
    # All retries failed
    # -----------------------------------------

    return {
        "status": "failed_after_retries",
        "records": None,
        "sample_date": None
    }


# -----------------------------------------
# 6. Main loop
# -----------------------------------------

results = []

for state, district, market in candidates:

    print()
    print("=" * 60)

    print(
        f"Testing: {state} | "
        f"{district} | "
        f"{market}"
    )

    print("=" * 60)

    result = get_market_data(
        state,
        district,
        market
    )

    print(
        "Records:",
        result["records"]
    )

    results.append({
        "state": state,
        "district": district,
        "market": market,
        "records": result["records"],
        "sample_date": result["sample_date"],
        "status": result["status"]
    })

    # -----------------------------------------
    # IMPORTANT:
    # Give API server time
    # -----------------------------------------

    print(
        "Waiting 5 seconds before next market..."
    )

    time.sleep(5)


# -----------------------------------------
# 7. DataFrame
# -----------------------------------------

df = pd.DataFrame(results)


# -----------------------------------------
# 8. Sort successful results
# -----------------------------------------

df["sort_records"] = (
    df["records"]
    .fillna(-1)
)

df = df.sort_values(
    "sort_records",
    ascending=False
)

df = df.drop(
    columns=["sort_records"]
)


# -----------------------------------------
# 9. Display
# -----------------------------------------

print()
print("=" * 70)
print("FINAL MARKET COMPARISON")
print("=" * 70)

print(
    df.to_string(index=False)
)


# -----------------------------------------
# 10. Save
# -----------------------------------------

output_file = (
    "data/processed/"
    "onion_candidate_markets.csv"
)

df.to_csv(
    output_file,
    index=False
)

print()
print("Saved:")
print(output_file)