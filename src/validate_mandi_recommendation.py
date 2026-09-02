import pandas as pd
import numpy as np


# ============================================================
# FILE
# ============================================================

FILE = (
    "data/processed/recommendation/"
    "mandi_profit_analysis.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading mandi profit analysis...")

df = pd.read_csv(FILE)

print(f"Rows loaded: {len(df):,}")


# ============================================================
# BASIC INFORMATION
# ============================================================

print("\n" + "=" * 70)
print("BASIC DATA CHECK")
print("=" * 70)

print(f"Markets: {df['market'].nunique()}")
print(f"Dates: {df['date'].nunique()}")


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "date",
    "market",
    "distance_km",
    "current_price",
    "predicted_price",
    "transport_cost",
    "market_fee",
    "gross_revenue",
    "total_cost",
    "net_return",
    "net_price_per_quintal",
    "rank",
    "recommendation"
]

for column in required_columns:

    if column not in df.columns:

        raise ValueError(
            f"Missing required column: {column}"
        )

print("\nAll required columns are present.")


# ============================================================
# MISSING VALUE CHECK
# ============================================================

print("\nChecking missing values...")

missing = df[required_columns].isna().sum()

missing = missing[missing > 0]

if len(missing) == 0:

    print("✓ No missing values found.")

else:

    print("✗ Missing values found:")
    print(missing)


# ============================================================
# DUPLICATE CHECK
# ============================================================

print("\nChecking duplicate date-market combinations...")

duplicates = df.duplicated(
    subset=["date", "market"]
).sum()

print(
    f"Duplicate date-market rows: {duplicates}"
)


# ============================================================
# DISTANCE VALIDATION
# ============================================================

print("\nChecking distances...")

negative_distance = (
    df["distance_km"] < 0
).sum()

print(
    f"Negative distances: {negative_distance}"
)

if negative_distance == 0:
    print("✓ Distance values are valid.")


# ============================================================
# PRICE VALIDATION
# ============================================================

print("\nChecking prices...")

negative_predicted = (
    df["predicted_price"] < 0
).sum()

negative_current = (
    df["current_price"] < 0
).sum()

print(
    f"Negative predicted prices: {negative_predicted}"
)

print(
    f"Negative current prices: {negative_current}"
)


# ============================================================
# PROFIT FORMULA VALIDATION
# ============================================================

print("\nChecking profit calculations...")

calculated_net_return = (
    df["gross_revenue"]
    - df["total_cost"]
)

profit_difference = (
    df["net_return"]
    - calculated_net_return
).abs()

wrong_profit = (
    profit_difference > 0.01
).sum()

print(
    f"Incorrect net-return calculations: {wrong_profit}"
)

if wrong_profit == 0:

    print(
        "✓ Net return calculation is correct."
    )


# ============================================================
# TRANSPORT COST VALIDATION
# ============================================================

print("\nChecking transportation calculations...")

# Current prototype values
TRANSPORT_COST_PER_QUINTAL_KM = 3.0
QUANTITY_QUINTALS = 10

expected_transport = (
    df["distance_km"]
    * TRANSPORT_COST_PER_QUINTAL_KM
    * QUANTITY_QUINTALS
)

transport_difference = (
    df["transport_cost"]
    - expected_transport
).abs()

wrong_transport = (
    transport_difference > 0.01
).sum()

print(
    f"Incorrect transport calculations: "
    f"{wrong_transport}"
)

if wrong_transport == 0:

    print(
        "✓ Transportation calculation is correct."
    )


# ============================================================
# RANK VALIDATION
# ============================================================

print("\nChecking mandi rankings...")

ranking_errors = 0

for date, group in df.groupby("date"):

    # Mandi having maximum net return
    expected_market = group.loc[
        group["net_return"].idxmax(),
        "market"
    ]

    # Mandi marked as rank 1
    rank_one = group[
        group["rank"] == 1
    ]

    if len(rank_one) == 0:

        ranking_errors += 1
        continue

    actual_market = rank_one.iloc[0]["market"]

    if expected_market != actual_market:

        ranking_errors += 1


print(
    f"Ranking errors: {ranking_errors}"
)

if ranking_errors == 0:

    print(
        "✓ Mandi ranking is mathematically correct."
    )


# ============================================================
# RECOMMENDATION VALIDATION
# ============================================================

print("\nChecking recommendations...")

recommendation_errors = 0

for date, group in df.groupby("date"):

    recommended = group[
        group["recommendation"] == "RECOMMENDED"
    ]

    if len(recommended) != 1:

        recommendation_errors += 1
        continue

    recommended_market = (
        recommended.iloc[0]["market"]
    )

    best_market = group.loc[
        group["net_return"].idxmax(),
        "market"
    ]

    if recommended_market != best_market:

        recommendation_errors += 1


print(
    f"Recommendation errors: "
    f"{recommendation_errors}"
)

if recommendation_errors == 0:

    print(
        "✓ Recommendation logic is correct."
    )


# ============================================================
# RECOMMENDATION DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("RECOMMENDATION DISTRIBUTION")
print("=" * 70)

recommendation_counts = (
    df[
        df["recommendation"] == "RECOMMENDED"
    ]
    ["market"]
    .value_counts()
)

print(recommendation_counts)


# ============================================================
# AVERAGE NET RETURN
# ============================================================

print("\n" + "=" * 70)
print("AVERAGE NET RETURN BY MARKET")
print("=" * 70)

summary = (
    df.groupby("market")
    .agg(
        observations=("market", "size"),
        avg_distance_km=("distance_km", "mean"),
        avg_predicted_price=("predicted_price", "mean"),
        avg_transport_cost=("transport_cost", "mean"),
        avg_net_return=("net_return", "mean"),
        avg_net_price=("net_price_per_quintal", "mean")
    )
    .sort_values(
        "avg_net_return",
        ascending=False
    )
)

print(
    summary.round(2).to_string()
)


# ============================================================
# FINAL VALIDATION RESULT
# ============================================================

print("\n" + "=" * 70)
print("FINAL VALIDATION")
print("=" * 70)

all_checks_passed = (
    len(missing) == 0
    and duplicates == 0
    and negative_distance == 0
    and negative_predicted == 0
    and negative_current == 0
    and wrong_profit == 0
    and wrong_transport == 0
    and ranking_errors == 0
    and recommendation_errors == 0
)


if all_checks_passed:

    print(
        "\n✓ ALL VALIDATION CHECKS PASSED"
    )

    print(
        "\nThe Onion mandi recommendation "
        "pipeline is internally consistent."
    )

else:

    print(
        "\n✗ SOME VALIDATION CHECKS FAILED"
    )

    print(
        "Review the errors above before "
        "moving to the next stage."
    )

print("\n" + "=" * 70)