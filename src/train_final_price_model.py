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

MODEL_DIR = Path(
    "data/processed/models/change_xgboost_v3"
)

VALIDATION_DIR = (
    MODEL_DIR /
    "validation_selection"
)

OUTPUT_DIR = (
    MODEL_DIR /
    "final"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# MARKETS
# ============================================================

MARKETS = [
    "bareilly",
    "bargarh",
    "nagpur"
]


# ============================================================
# MODEL PARAMETERS
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
# LOAD SELECTED FEATURE CONFIGURATION
# ============================================================

best_config_file = (
    VALIDATION_DIR /
    "best_validation_feature_configuration.csv"
)

best_config = pd.read_csv(
    best_config_file
)


# ============================================================
# RESULTS
# ============================================================

final_results = []


# ============================================================
# PROCESS EACH MARKET
# ============================================================

for market in MARKETS:

    print("\n")
    print("=" * 80)
    print(
        f"FINAL MODEL: {market.upper()}"
    )
    print("=" * 80)

    # ========================================================
    # SELECTED FEATURE COUNT
    # ========================================================

    selected_row = (
        best_config[
            best_config["market"]
            == market
        ]
        .iloc[0]
    )

    top_k = int(
        selected_row["top_k"]
    )

    print(
        f"Selected feature count: "
        f"{top_k}"
    )

    # ========================================================
    # LOAD ORIGINAL FEATURE IMPORTANCE
    # ========================================================

    importance_file = (
        MODEL_DIR /
        f"{market}_feature_importance.csv"
    )

    importance = pd.read_csv(
        importance_file
    )

    importance = importance.sort_values(
        "importance",
        ascending=False
    ).reset_index(drop=True)

    feature_columns = (
        importance
        .head(top_k)["feature"]
        .tolist()
    )

    print("\nSelected features:")

    for feature in feature_columns:

        print(
            f"  - {feature}"
        )

    # ========================================================
    # LOAD DATA
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
    # COMBINE TRAIN + VALIDATION
    # ========================================================

    train_full = pd.concat(
        [
            train,
            validation
        ],
        ignore_index=True
    )

    # ========================================================
    # CREATE TARGET
    # ========================================================

    train_full["price_change"] = (
        train_full["target_price"]
        - train_full["modal_price"]
    )

    test["price_change"] = (
        test["target_price"]
        - test["modal_price"]
    )

    # ========================================================
    # TRAINING DATA
    # ========================================================

    X_train = train_full[
        feature_columns
    ]

    y_train = train_full[
        "price_change"
    ]

    # ========================================================
    # TEST DATA
    # ========================================================

    X_test = test[
        feature_columns
    ]

    y_test = test[
        "price_change"
    ]

    # ========================================================
    # TRAIN FINAL MODEL
    # ========================================================

    model = xgb.XGBRegressor(
        **MODEL_PARAMS
    )

    print("\nTraining final model...")

    model.fit(
        X_train,
        y_train,
        verbose=False
    )

    print(
        "Final model trained."
    )

    # ========================================================
    # TEST PREDICTION
    # ========================================================

    predicted_change = model.predict(
        X_test
    )

    # ========================================================
    # RECONSTRUCT PRICE
    # ========================================================

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

    # ========================================================
    # PRICE METRICS
    # ========================================================

    test_mae = mean_absolute_error(
        actual_price,
        predicted_price
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

    # ========================================================
    # CHANGE METRICS
    # ========================================================

    test_change_mae = mean_absolute_error(
        y_test,
        predicted_change
    )

    test_change_rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predicted_change
        )
    )

    # ========================================================
    # DIRECTION
    # ========================================================

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

    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print("\n")
    print("-" * 60)
    print("FINAL TEST RESULTS")
    print("-" * 60)

    print(
        f"Test Price MAE       : "
        f"₹{test_mae:.2f}"
    )

    print(
        f"Test Price RMSE      : "
        f"₹{test_rmse:.2f}"
    )

    print(
        f"Test Price R²        : "
        f"{test_r2:.4f}"
    )

    print(
        f"Test Change MAE      : "
        f"₹{test_change_mae:.2f}"
    )

    print(
        f"Test Change RMSE     : "
        f"₹{test_change_rmse:.2f}"
    )

    print(
        f"Direction Accuracy   : "
        f"{direction_accuracy:.2f}%"
    )

    # ========================================================
    # SAVE PREDICTIONS
    # ========================================================

    predictions = pd.DataFrame({

        "date":
            test["date"].values,

        "modal_price":
            current_price,

        "actual_price":
            actual_price,

        "actual_change":
            y_test.to_numpy(),

        "predicted_change":
            predicted_change,

        "predicted_price":
            predicted_price,

        "price_error":
            actual_price
            - predicted_price,

        "absolute_error":
            np.abs(
                actual_price
                - predicted_price
            ),

        "actual_direction":
            np.where(
                y_test.to_numpy() > 0,
                "up",
                np.where(
                    y_test.to_numpy() < 0,
                    "down",
                    "same"
                )
            ),

        "predicted_direction":
            np.where(
                predicted_change > 0,
                "up",
                np.where(
                    predicted_change < 0,
                    "down",
                    "same"
                )
            )
    })

    prediction_file = (
        OUTPUT_DIR /
        f"{market}_final_predictions.csv"
    )

    predictions.to_csv(
        prediction_file,
        index=False
    )

    # ========================================================
    # SAVE MODEL
    # ========================================================

    model_file = (
        OUTPUT_DIR /
        f"{market}_final_model.json"
    )

    model.save_model(
        model_file
    )

    # ========================================================
    # SAVE FEATURE LIST
    # ========================================================

    feature_file = (
        OUTPUT_DIR /
        f"{market}_final_features.csv"
    )

    pd.DataFrame({
        "feature":
            feature_columns
    }).to_csv(
        feature_file,
        index=False
    )

    # ========================================================
    # STORE RESULTS
    # ========================================================

    final_results.append({

        "market":
            market,

        "selected_features":
            top_k,

        "train_rows":
            len(train),

        "validation_rows":
            len(validation),

        "final_training_rows":
            len(train_full),

        "test_rows":
            len(test),

        "test_price_mae":
            test_mae,

        "test_price_rmse":
            test_rmse,

        "test_price_r2":
            test_r2,

        "test_change_mae":
            test_change_mae,

        "test_change_rmse":
            test_change_rmse,

        "direction_accuracy":
            direction_accuracy
    })


# ============================================================
# SAVE FINAL RESULTS
# ============================================================

results_df = pd.DataFrame(
    final_results
)

results_file = (
    OUTPUT_DIR /
    "final_price_model_results.csv"
)

results_df.to_csv(
    results_file,
    index=False
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 80)
print(
    "FINAL PRICE-ONLY MODEL RESULTS"
)
print("=" * 80)

print(
    results_df.to_string(
        index=False
    )
)

print("\n")
print(
    "Final results saved to:"
)

print(
    results_file
)

print("\n")
print("=" * 80)
print(
    "FINAL PRICE MODEL COMPLETE"
)
print("=" * 80)