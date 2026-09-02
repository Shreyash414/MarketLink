import pandas as pd
import numpy as np
import xgboost as xgb

from pathlib import Path

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# ============================================================
# PATHS
# ============================================================

SPLIT_DIR = Path(
    "data/processed/splits_v3"
)

IMPORTANCE_DIR = Path(
    "data/processed/models/change_xgboost_v3/feature_selection"
)

OUTPUT_DIR = Path(
    "data/processed/models/change_xgboost_v3/feature_selection_results"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# MARKETS
# ============================================================

markets = [
    "bareilly",
    "bargarh",
    "nagpur"
]


# ============================================================
# TOP-K VALUES
# ============================================================

TOP_K_VALUES = [
    10,
    20,
    30,
    40,
    50
]


# ============================================================
# MODEL
# ============================================================

MODEL_PARAMS = {

    "n_estimators": 500,

    "learning_rate": 0.03,

    "max_depth": 3,

    "min_child_weight": 3,

    "subsample": 0.8,

    "colsample_bytree": 0.8,

    "reg_lambda": 1.0,

    "objective": "reg:squarederror",

    "random_state": 42,

    "n_jobs": -1
}


# ============================================================
# RESULTS
# ============================================================

all_results = []


# ============================================================
# LOOP THROUGH MARKETS
# ============================================================

for market in markets:

    print("\n")
    print("=" * 80)
    print(
        f"MARKET: {market.upper()}"
    )
    print("=" * 80)

    # ========================================================
    # LOAD SPLITS
    # ========================================================

    train = pd.read_csv(
        SPLIT_DIR /
        f"{market}_train.csv"
    )

    validation = pd.read_csv(
        SPLIT_DIR /
        f"{market}_validation.csv"
    )

    test = pd.read_csv(
        SPLIT_DIR /
        f"{market}_test.csv"
    )

    # ========================================================
    # CREATE TARGET
    # ========================================================

    for df in [
        train,
        validation,
        test
    ]:

        df["price_change"] = (
            df["target_price"]
            - df["modal_price"]
        )

    # ========================================================
    # TEST TOP-K
    # ========================================================

    for k in TOP_K_VALUES:

        print("\n")
        print(
            f"{market.upper()} "
            f"TOP {k} FEATURES"
        )
        print("-" * 60)

        importance_file = (
            IMPORTANCE_DIR /
            f"{market}_top_{k}_features.csv"
        )

        importance = pd.read_csv(
            importance_file
        )

        feature_columns = (
            importance["feature"]
            .tolist()
        )

        # ====================================================
        # X / Y
        # ====================================================

        X_train = train[
            feature_columns
        ]

        y_train = train[
            "price_change"
        ]

        X_validation = validation[
            feature_columns
        ]

        y_validation = validation[
            "price_change"
        ]

        X_test = test[
            feature_columns
        ]

        y_test = test[
            "price_change"
        ]

        # ====================================================
        # MODEL
        # ====================================================

        model = xgb.XGBRegressor(
            **MODEL_PARAMS
        )

        model.fit(
            X_train,
            y_train,
            eval_set=[
                (
                    X_validation,
                    y_validation
                )
            ],
            verbose=False
        )

        # ====================================================
        # VALIDATION
        # ====================================================

        validation_pred = model.predict(
            X_validation
        )

        validation_mae = (
            mean_absolute_error(
                y_validation,
                validation_pred
            )
        )

        validation_rmse = np.sqrt(
            mean_squared_error(
                y_validation,
                validation_pred
            )
        )

        validation_r2 = r2_score(
            y_validation,
            validation_pred
        )

        # ====================================================
        # TEST
        # ====================================================

        predicted_change = model.predict(
            X_test
        )

        current_price = (
            test["modal_price"]
            .to_numpy()
        )

        actual_price = (
            test["target_price"]
            .to_numpy()
        )

        predicted_price = (
            current_price
            + predicted_change
        )

        # ====================================================
        # PRICE METRICS
        # ====================================================

        test_mae = (
            mean_absolute_error(
                actual_price,
                predicted_price
            )
        )

        test_rmse = np.sqrt(
            mean_squared_error(
                actual_price,
                predicted_price
            )
        )

        test_r2 = r2_score(
            actual_price,
            predicted_price
        )

        # ====================================================
        # DIRECTION
        # ====================================================

        actual_direction = np.sign(
            y_test.to_numpy()
        )

        predicted_direction = np.sign(
            predicted_change
        )

        direction_accuracy = (
            np.mean(
                actual_direction
                == predicted_direction
            )
            * 100
        )

        # ====================================================
        # SAVE RESULT
        # ====================================================

        result = {

            "market":
                market,

            "top_k":
                k,

            "validation_mae":
                validation_mae,

            "validation_rmse":
                validation_rmse,

            "validation_r2":
                validation_r2,

            "test_mae":
                test_mae,

            "test_rmse":
                test_rmse,

            "test_r2":
                test_r2,

            "direction_accuracy":
                direction_accuracy
        }

        all_results.append(
            result
        )

        # ====================================================
        # PRINT
        # ====================================================

        print(
            f"Validation MAE : "
            f"{validation_mae:.2f}"
        )

        print(
            f"Validation R²  : "
            f"{validation_r2:.4f}"
        )

        print(
            f"Test MAE       : "
            f"₹{test_mae:.2f}"
        )

        print(
            f"Test RMSE      : "
            f"₹{test_rmse:.2f}"
        )

        print(
            f"Test R²        : "
            f"{test_r2:.4f}"
        )

        print(
            f"Direction       : "
            f"{direction_accuracy:.2f}%"
        )


# ============================================================
# SAVE RESULTS
# ============================================================

results_df = pd.DataFrame(
    all_results
)

results_file = (
    OUTPUT_DIR /
    "v3_feature_selection_results.csv"
)

results_df.to_csv(
    results_file,
    index=False
)


# ============================================================
# FINAL TABLE
# ============================================================

print("\n")
print("=" * 80)
print("V3 FEATURE SELECTION RESULTS")
print("=" * 80)

print(
    results_df.to_string(
        index=False
    )
)


# ============================================================
# BEST MODEL PER MARKET
# ============================================================

print("\n")
print("=" * 80)
print("BEST FEATURE COUNT PER MARKET")
print("=" * 80)

for market in markets:

    market_results = (
        results_df[
            results_df["market"]
            == market
        ]
        .sort_values(
            "test_mae"
        )
    )

    best = (
        market_results
        .iloc[0]
    )

    print(
        f"\n{market.upper()}"
    )

    print(
        f"Best features : "
        f"{int(best['top_k'])}"
    )

    print(
        f"Test MAE      : "
        f"₹{best['test_mae']:.2f}"
    )

    print(
        f"Test RMSE     : "
        f"₹{best['test_rmse']:.2f}"
    )

    print(
        f"Test R²       : "
        f"{best['test_r2']:.4f}"
    )

    print(
        f"Direction     : "
        f"{best['direction_accuracy']:.2f}%"
    )


print("\n")
print(
    f"Results saved to:\n"
    f"{results_file}"
)