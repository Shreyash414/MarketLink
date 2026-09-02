import pandas as pd
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

INPUT_PATH = (
    Path("data/processed/comparison")
    / "mandi_comparison.csv"
)

OUTPUT_DIR = Path(
    "data/processed/recommendation"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(INPUT_PATH)

df["date"] = pd.to_datetime(
    df["date"],
    errors="coerce"
)


# ============================================================
# RANKING
# ============================================================
#
# Higher risk-adjusted price = better opportunity.
#
# This is NOT farmer profit yet.
# It is only a model-based opportunity ranking.
# ============================================================

df["opportunity_score"] = (
    df["risk_adjusted_price"]
)


# ============================================================
# RANK MARKETS FOR EACH DATE
# ============================================================

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

df["recommendation"] = "ALTERNATIVE"

df.loc[
    df["rank"] == 1,
    "recommendation"
] = "RECOMMENDED"


# ============================================================
# SAVE DETAILED RANKING
# ============================================================

output_columns = [
    "date",
    "market",
    "current_price",
    "predicted_price",
    "expected_change",
    "expected_change_pct",
    "market_condition",
    "risk_level",
    "confidence_score",
    "risk_adjusted_price",
    "opportunity_score",
    "rank",
    "recommendation"
]

ranking = df[output_columns].copy()

ranking = ranking.sort_values(
    ["date", "rank", "market"]
).reset_index(drop=True)


ranking_path = (
    OUTPUT_DIR
    / "mandi_ranking.csv"
)

ranking.to_csv(
    ranking_path,
    index=False
)


# ============================================================
# BEST MANDI FOR EACH DATE
# ============================================================

recommended = ranking[
    ranking["rank"] == 1
].copy()


recommended_path = (
    OUTPUT_DIR
    / "recommended_mandi_by_date.csv"
)

recommended.to_csv(
    recommended_path,
    index=False
)


# ============================================================
# OVERALL MARKET PERFORMANCE
# ============================================================

market_summary = (
    ranking
    .groupby("market")
    .agg(
        observations=("market", "count"),
        average_predicted_price=(
            "predicted_price",
            "mean"
        ),
        average_risk_adjusted_price=(
            "risk_adjusted_price",
            "mean"
        ),
        average_expected_change_pct=(
            "expected_change_pct",
            "mean"
        ),
        average_confidence=(
            "confidence_score",
            "mean"
        ),
        recommended_count=(
            "recommendation",
            lambda x: (
                x == "RECOMMENDED"
            ).sum()
        )
    )
    .reset_index()
)


market_summary["recommendation_rate_pct"] = (
    market_summary["recommended_count"]
    / market_summary["observations"]
) * 100


market_summary = market_summary.sort_values(
    "recommended_count",
    ascending=False
)


summary_path = (
    OUTPUT_DIR
    / "market_recommendation_summary.csv"
)

market_summary.to_csv(
    summary_path,
    index=False
)


# ============================================================
# PRINT RESULTS
# ============================================================

print()
print("=" * 70)
print("MANDI RECOMMENDATION ENGINE")
print("=" * 70)

print(
    f"\nTotal observations: {len(ranking)}"
)

print(
    f"Dates compared: {ranking['date'].nunique()}"
)

print()
print("RECOMMENDED MANDI COUNT")
print(
    market_summary[
        [
            "market",
            "recommended_count",
            "recommendation_rate_pct"
        ]
    ].to_string(index=False)
)

print()
print("MARKET SUMMARY")
print(
    market_summary.to_string(
        index=False
    )
)

print()
print("LATEST COMPARISON")

latest_date = ranking["date"].max()

latest = ranking[
    ranking["date"] == latest_date
].copy()

print(
    latest[
        [
            "date",
            "market",
            "current_price",
            "predicted_price",
            "expected_change_pct",
            "risk_level",
            "confidence_score",
            "risk_adjusted_price",
            "rank",
            "recommendation"
        ]
    ].to_string(index=False)
)

print()
print("=" * 70)
print("FILES CREATED")
print("=" * 70)

print(
    f"Detailed ranking:"
    f"\n{ranking_path}"
)

print(
    f"\nRecommended mandi:"
    f"\n{recommended_path}"
)

print(
    f"\nMarket summary:"
    f"\n{summary_path}"
)