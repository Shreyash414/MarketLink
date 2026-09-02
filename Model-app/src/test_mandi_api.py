import os
import requests
import pandas as pd
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Get API key from .env
API_KEY = os.getenv("DATA_GOV_API_KEY")

# OGD resource
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"

URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

# API parameters
params = {
    "api-key": API_KEY,
    "format": "json",
    "offset": 0,
    "limit": 10
}

# Browser-like header
headers = {
    "User-Agent": "Mozilla/5.0"
}

try:
    print("Sending request...")

    response = requests.get(
        URL,
        params=params,
        headers=headers,
        timeout=(10, 90)
    )

    print("Response received!")
    print("Status code:", response.status_code)

    # Stop if server returned an error
    response.raise_for_status()

    # Convert JSON response to Python dictionary
    data = response.json()

    print("\nAPI status:", data.get("status"))
    print("Total records available:", data.get("total"))

    # Extract records
    records = data.get("records", [])

    print("Records received:", len(records))

    # Check whether records exist
    if not records:
        print("\nNo records received.")
        exit()

    # Convert records to DataFrame
    df = pd.DataFrame(records)

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nFirst 5 records:")
    print(df.head())

    # Save to CSV
    output_file = "data/raw/mandi_test_10.csv"

    df.to_csv(
        output_file,
        index=False
    )

    print(f"\nData saved successfully to: {output_file}")

except requests.exceptions.Timeout:
    print("\nERROR: The API request timed out.")

except requests.exceptions.HTTPError as e:
    print("\nERROR: API returned an HTTP error.")
    print(e)

except requests.exceptions.RequestException as e:
    print("\nERROR: Request failed.")
    print(e)

except Exception as e:
    print("\nERROR:", e)