import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE = Path("data/processed")

MARKETS = {
    "bareilly": BASE / "onion_bareilly_model.csv",
    "bargarh": BASE / "onion_bargarh_model.csv",
    "nagpur": BASE / "onion_nagpur_model.csv",
}

OUTPUT_DIR = BASE / "spike_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FUNCTION TO FIND COLUMN
# ============================================================

def find_column(df, possible_names):

    for name in possible_names:
        if name in df.columns:
            return name

    return None


# ============================================================
# SPIKE DETECTION
# ============================================================

def detect_spikes(df, market_name):

    df = df.copy()

    print("\n----------------------------------------")
    print(f"Processing {market_name}")
    print("----------------------------------------")

    # --------------------------------------------------------
    # Show available columns
    # --------------------------------------------------------

    print("Columns:")
    print(df.columns.tolist())

    # --------------------------------------------------------
    # Find date column
    # --------------------------------------------------------

    date_col = find_column(
        df,
        ["date", "Date", "Arrival_Date", "arrival_date"]
    )

    if date_col is None:
        raise ValueError(
            f"No date column found for {market_name}."
        )

    # --------------------------------------------------------
    # Find price column
    # --------------------------------------------------------

    price_col = find_column(
        df,
        [
            "modal_price",
            "Modal_Price",
            "modalPrice",
            "price"
        ]
    )

    if price_col is None:
        raise ValueError(
            f"No modal price column found for {market_name}."
        )

    print(f"Using date column  : {date_col}")
    print(f"Using price column : {price_col}")

    # --------------------------------------------------------
    # Convert date
    # --------------------------------------------------------

    df[date_col] = pd.to_datetime(
        df[date_col],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Convert price to numeric
    # --------------------------------------------------------

    df[price_col] = pd.to_numeric(
        df[price_col],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Remove invalid rows
    # --------------------------------------------------------

    df = df.dropna(
        subset=[date_col, price_col]
    ).copy()

    df = df[df[price_col] > 0].copy()

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    df = df.sort_values(
        date_col
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Remove duplicate dates if any
    # --------------------------------------------------------

    duplicate_dates = df.duplicated(
        subset=[date_col]
    ).sum()

    if duplicate_dates > 0:

        print(
            f"Removing {duplicate_dates} duplicate dates..."
        )

        df = df.drop_duplicates(
            subset=[date_col],
            keep="first"
        ).reset_index(drop=True)

    # --------------------------------------------------------
    # Next observed market-session price
    #
    # IMPORTANT:
    # We use the next available observation,
    # NOT the next calendar day.
    # --------------------------------------------------------

    df["next_price"] = df[price_col].shift(-1)

    # --------------------------------------------------------
    # Percentage price change
    # --------------------------------------------------------

    df["price_change_pct"] = (
        (
            df["next_price"] - df[price_col]
        )
        / df[price_col]
    ) * 100

    # --------------------------------------------------------
    # Remove final row
    #
    # It has no next observed price.
    # --------------------------------------------------------

    df = df.dropna(
        subset=["price_change_pct"]
    ).copy()

    # ========================================================
    # TRAINING PERIOD
    # ========================================================

    train_end = int(len(df) * 0.70)

    train_data = df.iloc[:train_end].copy()

    # Absolute percentage movements
    train_changes = train_data[
        "price_change_pct"
    ].abs()

    # --------------------------------------------------------
    # Calculate threshold from TRAINING DATA ONLY
    #
    # 95th percentile means roughly the largest
    # 5% of historical movements are considered unusual.
    # --------------------------------------------------------

    threshold = train_changes.quantile(0.95)

    # Prevent an extremely small threshold
    threshold = max(threshold, 10.0)

    print(
        f"Spike threshold: {threshold:.2f}%"
    )

    # ========================================================
    # SPIKE LABEL
    # ========================================================

    df["spike_threshold_pct"] = threshold

    df["is_spike"] = (
        df["price_change_pct"].abs()
        >= threshold
    ).astype(int)

    # --------------------------------------------------------
    # Market name
    # --------------------------------------------------------

    df["market"] = market_name

    # ========================================================
    # Spike type
    # ========================================================

    df["spike_type"] = "normal"

    df.loc[
        (
            df["is_spike"] == 1
        )
        &
        (
            df["price_change_pct"] > 0
        ),
        "spike_type"
    ] = "upward_spike"

    df.loc[
        (
            df["is_spike"] == 1
        )
        &
        (
            df["price_change_pct"] < 0
        ),
        "spike_type"
    ] = "downward_spike"

    # ========================================================
    # SAVE DATA
    # ========================================================

    output_columns = [
        date_col,
        "market",
        price_col,
        "next_price",
        "price_change_pct",
        "spike_threshold_pct",
        "is_spike",
        "spike_type"
    ]

    output = df[output_columns].copy()

    output_path = (
        OUTPUT_DIR
        / f"{market_name}_spikes.csv"
    )

    output.to_csv(
        output_path,
        index=False
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    total = len(output)

    spikes = int(
        output["is_spike"].sum()
    )

    normal = total - spikes

    upward_spikes = int(
        (
            output["spike_type"]
            == "upward_spike"
        ).sum()
    )

    downward_spikes = int(
        (
            output["spike_type"]
            == "downward_spike"
        ).sum()
    )

    spike_percentage = (
        spikes / total
    ) * 100 if total > 0 else 0

    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print()
    print(f"Total observations : {total}")
    print(f"Normal observations: {normal}")
    print(f"Spikes             : {spikes}")
    print(f"Upward spikes      : {upward_spikes}")
    print(f"Downward spikes    : {downward_spikes}")
    print(
        f"Spike percentage   : {spike_percentage:.2f}%"
    )

    print(
        f"Saved to: {output_path}"
    )

    # ========================================================
    # RETURN SUMMARY
    # ========================================================

    return {
        "market": market_name,
        "total_observations": total,
        "normal_observations": normal,
        "spikes": spikes,
        "upward_spikes": upward_spikes,
        "downward_spikes": downward_spikes,
        "spike_percentage": spike_percentage,
        "threshold_pct": threshold
    }


# ============================================================
# MAIN
# ============================================================

results = []


for market, path in MARKETS.items():

    if not path.exists():

        print(
            f"\nERROR: File not found:"
            f"\n{path}"
        )

        continue

    try:

        df = pd.read_csv(path)

        result = detect_spikes(
            df,
            market
        )

        results.append(result)

    except Exception as e:

        print(
            f"\nERROR processing {market}:"
        )

        print(e)


# ============================================================
# CREATE SUMMARY
# ============================================================

if results:

    summary = pd.DataFrame(
        results
    )

    summary_path = (
        OUTPUT_DIR
        / "spike_summary.csv"
    )

    summary.to_csv(
        summary_path,
        index=False
    )

    print("\n")
    print("=" * 60)
    print("FINAL SPIKE SUMMARY")
    print("=" * 60)

    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print(
        f"Summary saved to:"
        f"\n{summary_path}"
    )

else:

    print(
        "\nNo market results were generated."
    )