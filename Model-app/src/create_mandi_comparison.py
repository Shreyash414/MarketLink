import pandas as pd
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE = Path("data/processed")

PREDICTION_DIR = (
    BASE
    / "models"
    / "change_xgboost_v3"
)

CONFIDENCE_DIR = (
    BASE
    / "confidence"
)

OUTPUT_DIR = (
    BASE
    / "comparison"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


MARKETS = [
    "bareilly",
    "bargarh",
    "nagpur"
]


# ============================================================
# PROCESS ONE MARKET
# ============================================================

def process_market(market):

    print()
    print("=" * 60)
    print(f"PROCESSING {market.upper()}")
    print("=" * 60)

    prediction_path = (
        PREDICTION_DIR
        / f"{market}_test_predictions.csv"
    )

    confidence_path = (
        CONFIDENCE_DIR
        / f"{market}_confidence.csv"
    )

    if not prediction_path.exists():
        print(
            f"Prediction file not found:\n"
            f"{prediction_path}"
        )
        return None

    if not confidence_path.exists():
        print(
            f"Confidence file not found:\n"
            f"{confidence_path}"
        )
        return None

    # --------------------------------------------------------
    # Load files
    # --------------------------------------------------------

    predictions = pd.read_csv(
        prediction_path
    )

    confidence = pd.read_csv(
        confidence_path
    )

    predictions["date"] = pd.to_datetime(
        predictions["date"],
        errors="coerce"
    )

    confidence["date"] = pd.to_datetime(
        confidence["date"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Keep required confidence columns
    # --------------------------------------------------------

    confidence_columns = [
        "date",
        "market_condition",
        "risk_level",
        "confidence_score"
    ]

    confidence = confidence[
        confidence_columns
    ].copy()

    # --------------------------------------------------------
    # Merge prediction + confidence
    # --------------------------------------------------------

    df = pd.merge(
        predictions,
        confidence,
        on="date",
        how="inner"
    )

    # --------------------------------------------------------
    # Add market
    # --------------------------------------------------------

    df["market"] = market

    # --------------------------------------------------------
    # Current price
    # --------------------------------------------------------

    df["current_price"] = (
        df["modal_price"]
    )

    # --------------------------------------------------------
    # Expected price change
    # --------------------------------------------------------

    df["expected_change"] = (
        df["predicted_price"]
        - df["current_price"]
    )

    # --------------------------------------------------------
    # Expected percentage change
    # --------------------------------------------------------

    df["expected_change_pct"] = (
        df["expected_change"]
        / df["current_price"]
    ) * 100

    # --------------------------------------------------------
    # Risk adjustment
    #
    # IMPORTANT:
    # These are prototype weights.
    # They are NOT probability estimates.
    # --------------------------------------------------------

    reliability_factor = {
        "LOW": 1.00,
        "MEDIUM": 0.85,
        "HIGH": 0.60
    }

    df["reliability_factor"] = (
        df["risk_level"]
        .map(reliability_factor)
    )

    # --------------------------------------------------------
    # Risk-adjusted predicted price
    # --------------------------------------------------------

    df["risk_adjusted_price"] = (
        df["current_price"]
        +
        (
            df["expected_change"]
            * df["reliability_factor"]
        )
    )

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    df["expected_direction"] = "STABLE"

    df.loc[
        df["expected_change_pct"] > 1,
        "expected_direction"
    ] = "UP"

    df.loc[
        df["expected_change_pct"] < -1,
        "expected_direction"
    ] = "DOWN"

    # --------------------------------------------------------
    # Select final columns
    # --------------------------------------------------------

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
        "reliability_factor",
        "risk_adjusted_price",
        "expected_direction"
    ]

    output = df[
        output_columns
    ].copy()

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    output = output.sort_values(
        "date"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_path = (
        OUTPUT_DIR
        / f"{market}_comparison.csv"
    )

    output.to_csv(
        output_path,
        index=False
    )

    print(
        f"Matched rows: {len(output)}"
    )

    print(
        f"Saved: {output_path}"
    )

    return output


# ============================================================
# CREATE ALL MARKET COMPARISON
# ============================================================

all_markets = []

for market in MARKETS:

    result = process_market(
        market
    )

    if result is not None:
        all_markets.append(result)


# ============================================================
# COMBINE ALL MARKETS
# ============================================================

if all_markets:

    combined = pd.concat(
        all_markets,
        ignore_index=True
    )

    combined_path = (
        OUTPUT_DIR
        / "mandi_comparison.csv"
    )

    combined.to_csv(
        combined_path,
        index=False
    )

    print()
    print("=" * 60)
    print("COMBINED MANDI COMPARISON")
    print("=" * 60)

    print(
        combined.tail(
            10
        ).to_string(index=False)
    )

    print()
    print(
        f"Saved: {combined_path}"
    )

else:

    print(
        "No comparison data generated."
    )