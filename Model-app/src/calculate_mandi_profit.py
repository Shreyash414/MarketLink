import pandas as pd
import numpy as np
import os


# ============================================================
# CONFIGURATION
# ============================================================

# Example farmer location
# We will later replace this with actual farmer GPS coordinates.
FARMER_LATITUDE = 28.6139
FARMER_LONGITUDE = 77.2090

# Quantity of onions to sell
QUANTITY_QUINTALS = 10

# Estimated transportation cost
# ₹ per quintal per kilometer
TRANSPORT_COST_PER_QUINTAL_KM = 3.0

# Estimated mandi fee
# ₹ per quintal
MARKET_FEE_PER_QUINTAL = 20.0


# ============================================================
# FILE PATHS
# ============================================================

COMPARISON_FILE = "data/processed/comparison/mandi_comparison.csv"
METADATA_FILE = "data/processed/market_metadata.csv"

OUTPUT_DIR = "data/processed/recommendation"

PROFIT_OUTPUT = (
    f"{OUTPUT_DIR}/mandi_profit_analysis.csv"
)

RECOMMENDATION_OUTPUT = (
    f"{OUTPUT_DIR}/final_mandi_recommendations.csv"
)


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two geographic coordinates.

    Returns distance in kilometers.
    """

    R = 6371.0

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)

    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arctan2(
        np.sqrt(a),
        np.sqrt(1 - a)
    )

    return R * c


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading mandi comparison data...")

comparison = pd.read_csv(COMPARISON_FILE)

print(
    f"Comparison records loaded: {len(comparison):,}"
)

print("\nLoading mandi metadata...")

metadata = pd.read_csv(METADATA_FILE)

print(
    f"Market metadata loaded: {len(metadata)}"
)


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

comparison_required = [
    "date",
    "market",
    "current_price",
    "predicted_price",
    "expected_change",
    "expected_change_pct",
    "market_condition",
    "risk_level",
    "confidence_score",
    "reliability_factor",
    "risk_adjusted_price",
    "expected_direction"
]

metadata_required = [
    "market",
    "state",
    "district",
    "latitude",
    "longitude"
]


for column in comparison_required:

    if column not in comparison.columns:
        raise ValueError(
            f"Missing column in comparison file: {column}"
        )


for column in metadata_required:

    if column not in metadata.columns:
        raise ValueError(
            f"Missing column in metadata file: {column}"
        )


print("\nAll required columns found.")


# ============================================================
# CLEAN MARKET NAMES
# ============================================================

comparison["market"] = (
    comparison["market"]
    .astype(str)
    .str.strip()
    .str.lower()
)

metadata["market"] = (
    metadata["market"]
    .astype(str)
    .str.strip()
    .str.lower()
)


# ============================================================
# MERGE PREDICTIONS WITH MARKET LOCATION
# ============================================================

print("\nMerging predictions with market coordinates...")

df = comparison.merge(
    metadata,
    on="market",
    how="left",
    validate="many_to_one"
)


# ============================================================
# CHECK MISSING COORDINATES
# ============================================================

missing_coordinates = df[
    df["latitude"].isna()
    | df["longitude"].isna()
]["market"].unique()


if len(missing_coordinates) > 0:

    raise ValueError(
        "Missing coordinates for markets: "
        + ", ".join(missing_coordinates)
    )


# ============================================================
# CALCULATE DISTANCE
# ============================================================

print("\nCalculating distance from farmer to each mandi...")

df["distance_km"] = haversine_distance(
    FARMER_LATITUDE,
    FARMER_LONGITUDE,
    df["latitude"].astype(float),
    df["longitude"].astype(float)
)


# ============================================================
# TRANSPORT COST
# ============================================================

df["transport_cost"] = (
    df["distance_km"]
    * TRANSPORT_COST_PER_QUINTAL_KM
    * QUANTITY_QUINTALS
)


# ============================================================
# MARKET FEE
# ============================================================

df["market_fee"] = (
    MARKET_FEE_PER_QUINTAL
    * QUANTITY_QUINTALS
)


# ============================================================
# GROSS REVENUE
# ============================================================

# predicted_price is ₹ per quintal
#
# Example:
# predicted price = ₹2500
# quantity = 10 quintals
#
# gross revenue = 2500 × 10 = ₹25,000

df["gross_revenue"] = (
    df["predicted_price"]
    * QUANTITY_QUINTALS
)


# ============================================================
# TOTAL COST
# ============================================================

df["total_cost"] = (
    df["transport_cost"]
    + df["market_fee"]
)


# ============================================================
# NET RETURN
# ============================================================

df["net_return"] = (
    df["gross_revenue"]
    - df["total_cost"]
)


# ============================================================
# NET PRICE PER QUINTAL
# ============================================================

df["net_price_per_quintal"] = (
    df["net_return"]
    / QUANTITY_QUINTALS
)


# ============================================================
# CURRENT NET RETURN
# ============================================================

# current_price = current mandi price
#
# This lets us compare:
#
# Current net return
# vs
# Expected future net return

df["current_gross_revenue"] = (
    df["current_price"]
    * QUANTITY_QUINTALS
)

df["current_net_return"] = (
    df["current_gross_revenue"]
    - df["total_cost"]
)


# ============================================================
# EXPECTED NET GAIN
# ============================================================

df["expected_net_gain"] = (
    df["net_return"]
    - df["current_net_return"]
)


# ============================================================
# OPPORTUNITY SCORE
# ============================================================

# For now:
#
# Higher expected net return = better opportunity

df["opportunity_score"] = (
    df["net_return"]
)


# ============================================================
# RANK MANDIS FOR EACH DATE
# ============================================================

print("\nRanking mandis based on expected net return...")

df["rank"] = (
    df.groupby("date")["opportunity_score"]
    .rank(
        ascending=False,
        method="min"
    )
)


# ============================================================
# RECOMMENDATION
# ============================================================

df["recommendation"] = np.where(
    df["rank"] == 1,
    "RECOMMENDED",
    "ALTERNATIVE"
)


# ============================================================
# SORT
# ============================================================

df = df.sort_values(
    ["date", "rank", "market"]
).reset_index(drop=True)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# SAVE COMPLETE ANALYSIS
# ============================================================

df.to_csv(
    PROFIT_OUTPUT,
    index=False
)


# ============================================================
# SAVE RECOMMENDED MANDI PER DATE
# ============================================================

recommended = df[
    df["rank"] == 1
].copy()


recommended = recommended[
    [
        "date",
        "market",
        "state",
        "district",
        "distance_km",
        "current_price",
        "predicted_price",
        "expected_change",
        "expected_change_pct",
        "risk_level",
        "confidence_score",
        "transport_cost",
        "market_fee",
        "gross_revenue",
        "total_cost",
        "net_return",
        "net_price_per_quintal",
        "expected_net_gain",
        "rank",
        "recommendation"
    ]
]


recommended.to_csv(
    RECOMMENDATION_OUTPUT,
    index=False
)


# ============================================================
# DISPLAY BASIC SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("MANDI PROFIT ANALYSIS COMPLETED")
print("=" * 70)

print(
    f"\nFarmer location:"
    f" ({FARMER_LATITUDE}, {FARMER_LONGITUDE})"
)

print(
    f"Quantity: {QUANTITY_QUINTALS} quintals"
)

print(
    f"Transport cost:"
    f" ₹{TRANSPORT_COST_PER_QUINTAL_KM}/quintal/km"
)

print(
    f"Market fee:"
    f" ₹{MARKET_FEE_PER_QUINTAL}/quintal"
)

print(
    f"\nTotal observations: {len(df):,}"
)

print(
    f"Unique dates: {df['date'].nunique():,}"
)

print(
    f"Markets: {df['market'].nunique()}"
)


# ============================================================
# MARKET SUMMARY
# ============================================================

print("\nAverage results by mandi:")

market_summary = (
    df.groupby("market")
    .agg(
        average_distance_km=("distance_km", "mean"),
        average_predicted_price=("predicted_price", "mean"),
        average_transport_cost=("transport_cost", "mean"),
        average_net_return=("net_return", "mean"),
        average_net_price=("net_price_per_quintal", "mean"),
        recommended_count=(
            "recommendation",
            lambda x: (x == "RECOMMENDED").sum()
        )
    )
    .sort_values(
        "average_net_return",
        ascending=False
    )
)

print(
    market_summary.round(2).to_string()
)


# ============================================================
# OUTPUT FILES
# ============================================================

print("\n" + "=" * 70)

print(
    f"\nComplete analysis saved to:"
    f"\n{PROFIT_OUTPUT}"
)

print(
    f"\nFinal recommendations saved to:"
    f"\n{RECOMMENDATION_OUTPUT}"
)

print("\n" + "=" * 70)