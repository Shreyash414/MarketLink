import os
import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

SPLIT_DIR = "data/processed/splits"
OUTPUT_DIR = "data/processed/models"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


MARKETS = [
    "Bareilly",
    "Bargarh",
    "Nagpur"
]


# ============================================================
# LOAD DATA
# ============================================================

def load_split(market, split):

    filename = (
        f"{market.lower()}_{split}.csv"
    )

    path = os.path.join(
        SPLIT_DIR,
        filename
    )

    df = pd.read_csv(path)

    df["date"] = pd.to_datetime(
        df["date"]
    )

    return df


# ============================================================
# METRICS
# ============================================================

def calculate_mae(actual, predicted):

    return np.mean(
        np.abs(
            actual - predicted
        )
    )


def calculate_rmse(actual, predicted):

    return np.sqrt(
        np.mean(
            (actual - predicted) ** 2
        )
    )


def calculate_mape(actual, predicted):

    # Avoid division by zero

    mask = actual != 0

    return np.mean(
        np.abs(
            (
                actual[mask]
                -
                predicted[mask]
            )
            /
            actual[mask]
        )
    ) * 100


# ============================================================
# EVALUATE MODEL
# ============================================================

def evaluate_model(
    actual,
    predicted
):

    mae = calculate_mae(
        actual,
        predicted
    )

    rmse = calculate_rmse(
        actual,
        predicted
    )

    mape = calculate_mape(
        actual,
        predicted
    )

    return mae, rmse, mape


# ============================================================
# CREATE BASELINE PREDICTIONS
# ============================================================

def create_predictions(
    train,
    validation,
    test
):

    # --------------------------------------------------------
    # Combine train + validation + test
    #
    # We need historical prices immediately before each
    # validation/test observation.
    # --------------------------------------------------------

    full = pd.concat(
        [
            train,
            validation,
            test
        ],
        ignore_index=True
    )

    full = full.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Naive prediction
    #
    # Next price = previous observed price
    # --------------------------------------------------------

    full["naive_prediction"] = (
        full["modal_price"]
        .shift(1)
    )

    # --------------------------------------------------------
    # 7-observation moving average
    # --------------------------------------------------------

    full["mean_7_prediction"] = (
        full["modal_price"]
        .shift(1)
        .rolling(7)
        .mean()
    )

    # --------------------------------------------------------
    # 30-observation moving average
    # --------------------------------------------------------

    full["mean_30_prediction"] = (
        full["modal_price"]
        .shift(1)
        .rolling(30)
        .mean()
    )

    # --------------------------------------------------------
    # Return only validation + test
    # --------------------------------------------------------

    validation_dates = set(
        validation["date"]
    )

    test_dates = set(
        test["date"]
    )

    validation_result = full[
        full["date"].isin(
            validation_dates
        )
    ].copy()

    test_result = full[
        full["date"].isin(
            test_dates
        )
    ].copy()

    return validation_result, test_result


# ============================================================
# EVALUATE ONE MARKET
# ============================================================

def evaluate_market(market):

    print("\n")
    print("=" * 80)
    print(f"BASELINE — {market}")
    print("=" * 80)

    train = load_split(
        market,
        "train"
    )

    validation = load_split(
        market,
        "validation"
    )

    test = load_split(
        market,
        "test"
    )

    validation_result, test_result = (
        create_predictions(
            train,
            validation,
            test
        )
    )

    results = []

    # ========================================================
    # VALIDATION
    # ========================================================

    print("\nVALIDATION RESULTS")

    actual = validation_result[
        "target_price"
    ].values

    for model_name in [
        "naive_prediction",
        "mean_7_prediction",
        "mean_30_prediction"
    ]:

        predicted = validation_result[
            model_name
        ].values

        mask = ~np.isnan(
            predicted
        )

        mae, rmse, mape = evaluate_model(
            actual[mask],
            predicted[mask]
        )

        print(
            f"\n{model_name}"
        )

        print(
            f"MAE  : ₹{mae:.2f}"
        )

        print(
            f"RMSE : ₹{rmse:.2f}"
        )

        print(
            f"MAPE : {mape:.2f}%"
        )

        results.append(
            {
                "market": market,
                "dataset": "validation",
                "model": model_name,
                "MAE": mae,
                "RMSE": rmse,
                "MAPE": mape
            }
        )

    # ========================================================
    # TEST
    # ========================================================

    print("\nTEST RESULTS")

    actual = test_result[
        "target_price"
    ].values

    for model_name in [
        "naive_prediction",
        "mean_7_prediction",
        "mean_30_prediction"
    ]:

        predicted = test_result[
            model_name
        ].values

        mask = ~np.isnan(
            predicted
        )

        mae, rmse, mape = evaluate_model(
            actual[mask],
            predicted[mask]
        )

        print(
            f"\n{model_name}"
        )

        print(
            f"MAE  : ₹{mae:.2f}"
        )

        print(
            f"RMSE : ₹{rmse:.2f}"
        )

        print(
            f"MAPE : {mape:.2f}%"
        )

        results.append(
            {
                "market": market,
                "dataset": "test",
                "model": model_name,
                "MAE": mae,
                "RMSE": rmse,
                "MAPE": mape
            }
        )

    # ========================================================
    # SAVE PREDICTIONS
    # ========================================================

    validation_path = os.path.join(
        OUTPUT_DIR,
        f"{market.lower()}_baseline_validation.csv"
    )

    test_path = os.path.join(
        OUTPUT_DIR,
        f"{market.lower()}_baseline_test.csv"
    )

    validation_result.to_csv(
        validation_path,
        index=False
    )

    test_result.to_csv(
        test_path,
        index=False
    )

    print(
        "\nSaved validation predictions:",
        validation_path
    )

    print(
        "Saved test predictions:",
        test_path
    )

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 80)
    print("BASELINE PRICE FORECASTING")
    print("=" * 80)

    all_results = []

    for market in MARKETS:

        results = evaluate_market(
            market
        )

        all_results.extend(
            results
        )

    # ========================================================
    # RESULTS TABLE
    # ========================================================

    results_df = pd.DataFrame(
        all_results
    )

    results_path = os.path.join(
        OUTPUT_DIR,
        "baseline_results.csv"
    )

    results_df.to_csv(
        results_path,
        index=False
    )

    print("\n")
    print("=" * 80)
    print("FINAL BASELINE RESULTS")
    print("=" * 80)

    print(
        results_df.round(2).to_string(
            index=False
        )
    )

    print("\nSaved:")
    print(results_path)

    print("\n")
    print("=" * 80)
    print("BASELINE TRAINING COMPLETE")
    print("=" * 80)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()