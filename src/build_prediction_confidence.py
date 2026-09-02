import pandas as pd
import numpy as np
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

SPIKE_DIR = (
    BASE
    / "spike_analysis"
)

OUTPUT_DIR = (
    BASE
    / "confidence"
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

    # --------------------------------------------------------
    # Files
    # --------------------------------------------------------

    prediction_path = (
        PREDICTION_DIR
        / f"{market}_test_predictions.csv"
    )

    spike_path = (
        SPIKE_DIR
        / f"{market}_spikes.csv"
    )

    if not prediction_path.exists():

        print(
            f"Prediction file not found:\n"
            f"{prediction_path}"
        )

        return None

    if not spike_path.exists():

        print(
            f"Spike file not found:\n"
            f"{spike_path}"
        )

        return None

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    predictions = pd.read_csv(
        prediction_path
    )

    spikes = pd.read_csv(
        spike_path
    )

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    predictions["date"] = pd.to_datetime(
        predictions["date"],
        errors="coerce"
    )

    spikes["date"] = pd.to_datetime(
        spikes["date"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Select spike information
    # --------------------------------------------------------

    spike_columns = [
        "date",
        "is_spike",
        "spike_type",
        "price_change_pct",
        "spike_threshold_pct"
    ]

    spikes = spikes[spike_columns].copy()

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    df = pd.merge(
        predictions,
        spikes,
        on="date",
        how="inner"
    )

    print(
        f"Prediction rows : {len(predictions)}"
    )

    print(
        f"Matched rows    : {len(df)}"
    )

    # --------------------------------------------------------
    # Prediction error
    # --------------------------------------------------------

    df["absolute_error"] = (
        df["target_price"]
        - df["predicted_price"]
    ).abs()

    # ========================================================
    # RECENT VOLATILITY
    # ========================================================
    #
    # We calculate volatility from the historical price
    # movement available at the prediction date.
    #
    # IMPORTANT:
    # We use price_change_pct from the CURRENT observation
    # and shift it so that future information is not used.
    #
    # ========================================================

    price_changes = pd.to_numeric(
        spikes["price_change_pct"],
        errors="coerce"
    )

    # The spike file is already chronological.
    spikes = spikes.sort_values(
        "date"
    ).reset_index(drop=True)

    # Historical movement before current date
    spikes["historical_volatility_7"] = (
        price_changes
        .shift(1)
        .rolling(7, min_periods=3)
        .std()
    )

    volatility = spikes[
        [
            "date",
            "historical_volatility_7"
        ]
    ]

    df = pd.merge(
        df,
        volatility,
        on="date",
        how="left"
    )

    # ========================================================
    # RISK CLASSIFICATION
    # ========================================================

    df["risk_level"] = "LOW"

    # --------------------------------------------------------
    # Medium risk:
    # elevated historical volatility
    # --------------------------------------------------------

    volatility_values = (
        df["historical_volatility_7"]
        .dropna()
    )

    if len(volatility_values) > 0:

        volatility_threshold = (
            volatility_values.quantile(0.75)
        )

    else:

        volatility_threshold = np.inf

    df.loc[
        df["historical_volatility_7"]
        >= volatility_threshold,
        "risk_level"
    ] = "MEDIUM"

    # --------------------------------------------------------
    # High risk:
    # current observation is classified as a spike
    # --------------------------------------------------------

    df.loc[
        df["is_spike"] == 1,
        "risk_level"
    ] = "HIGH"

    # ========================================================
    # CONFIDENCE SCORE
    # ========================================================

    confidence_map = {
        "LOW": 85,
        "MEDIUM": 60,
        "HIGH": 30
    }

    df["confidence_score"] = (
        df["risk_level"]
        .map(confidence_map)
    )

    # ========================================================
    # MARKET CONDITION
    # ========================================================

    df["market_condition"] = np.where(
        df["is_spike"] == 1,
        "UNUSUAL_VOLATILITY",
        np.where(
            df["risk_level"] == "MEDIUM",
            "ELEVATED_VOLATILITY",
            "NORMAL"
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    output_columns = [
        "date",
        "modal_price",
        "target_price",
        "predicted_price",
        "absolute_error",
        "price_change_pct",
        "historical_volatility_7",
        "is_spike",
        "spike_type",
        "market_condition",
        "risk_level",
        "confidence_score"
    ]

    output = df[
        output_columns
    ].copy()

    output_path = (
        OUTPUT_DIR
        / f"{market}_confidence.csv"
    )

    output.to_csv(
        output_path,
        index=False
    )

    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    print()
    print("RISK DISTRIBUTION")

    print(
        output["risk_level"]
        .value_counts()
        .to_string()
    )

    print()
    print("AVERAGE ERROR BY RISK")

    error_by_risk = (
        output
        .groupby("risk_level")["absolute_error"]
        .agg(
            observations="count",
            mean_error="mean",
            median_error="median"
        )
    )

    print(
        error_by_risk.to_string()
    )

    print()
    print(
        f"Volatility threshold: "
        f"{volatility_threshold:.2f}%"
    )

    print(
        f"Saved: {output_path}"
    )

    # ========================================================
    # SUMMARY ROWS
    # ========================================================

    result = []

    for risk in [
        "LOW",
        "MEDIUM",
        "HIGH"
    ]:

        subset = output[
            output["risk_level"] == risk
        ]

        if len(subset) == 0:
            continue

        result.append(
            {
                "market": market,
                "risk_level": risk,
                "observations": len(subset),
                "average_error": subset[
                    "absolute_error"
                ].mean(),
                "median_error": subset[
                    "absolute_error"
                ].median(),
                "average_confidence": subset[
                    "confidence_score"
                ].mean()
            }
        )

    return result


# ============================================================
# MAIN
# ============================================================

all_results = []

for market in MARKETS:

    try:

        results = process_market(
            market
        )

        if results:

            all_results.extend(
                results
            )

    except Exception as e:

        print()
        print(
            f"ERROR processing {market}:"
        )

        print(e)


# ============================================================
# SAVE SUMMARY
# ============================================================

if all_results:

    summary = pd.DataFrame(
        all_results
    )

    summary_path = (
        OUTPUT_DIR
        / "confidence_summary.csv"
    )

    summary.to_csv(
        summary_path,
        index=False
    )

    print()
    print("=" * 60)
    print("FINAL CONFIDENCE SUMMARY")
    print("=" * 60)

    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print(
        f"Saved: {summary_path}"
    )

else:

    print(
        "No confidence results generated."
    )