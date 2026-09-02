import os
import pandas as pd
import numpy as np

from xgboost import XGBRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# ============================================================
# CONFIGURATION
# ============================================================

MARKETS = [
    "bareilly",
    "bargarh",
    "nagpur"
]

SPLIT_DIR = "data/processed/splits"

OUTPUT_DIR = "data/processed/models/xgboost_tuning"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(y_true, y_pred):

    mae = mean_absolute_error(
        y_true,
        y_pred
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_true,
            y_pred
        )
    )

    non_zero = y_true != 0

    if non_zero.sum() > 0:

        mape = np.mean(
            np.abs(
                (
                    y_true[non_zero]
                    - y_pred[non_zero]
                )
                / y_true[non_zero]
            )
        ) * 100

    else:

        mape = np.nan

    r2 = r2_score(
        y_true,
        y_pred
    )

    return mae, rmse, mape, r2


# ============================================================
# FEATURE SELECTION
# ============================================================

def get_feature_columns(df):

    excluded_columns = [
        "date",
        "target_price",
        "market",
        "commodity",
        "variety",
        "grade"
    ]

    features = []

    for column in df.columns:

        if column in excluded_columns:
            continue

        if pd.api.types.is_numeric_dtype(
            df[column]
        ):
            features.append(column)

    return features


# ============================================================
# XGBOOST CONFIGURATIONS
# ============================================================

PARAMETER_CONFIGS = [

    {
        "name": "config_1",
        "n_estimators": 300,
        "learning_rate": 0.05,
        "max_depth": 3,
        "min_child_weight": 3,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0,
        "reg_lambda": 1
    },

    {
        "name": "config_2",
        "n_estimators": 500,
        "learning_rate": 0.03,
        "max_depth": 3,
        "min_child_weight": 3,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0,
        "reg_lambda": 1
    },

    {
        "name": "config_3",
        "n_estimators": 500,
        "learning_rate": 0.03,
        "max_depth": 5,
        "min_child_weight": 3,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0,
        "reg_lambda": 1
    },

    {
        "name": "config_4",
        "n_estimators": 700,
        "learning_rate": 0.03,
        "max_depth": 5,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0,
        "reg_lambda": 1
    },

    {
        "name": "config_5",
        "n_estimators": 500,
        "learning_rate": 0.02,
        "max_depth": 6,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 2
    },

    {
        "name": "config_6",
        "n_estimators": 700,
        "learning_rate": 0.02,
        "max_depth": 4,
        "min_child_weight": 5,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "reg_alpha": 0.1,
        "reg_lambda": 2
    },

    {
        "name": "config_7",
        "n_estimators": 800,
        "learning_rate": 0.02,
        "max_depth": 3,
        "min_child_weight": 5,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "reg_alpha": 0.1,
        "reg_lambda": 2
    },

    {
        "name": "config_8",
        "n_estimators": 400,
        "learning_rate": 0.05,
        "max_depth": 6,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 2
    }
]


# ============================================================
# TUNE ONE MARKET
# ============================================================

def tune_market(market):

    print("\n")
    print("=" * 70)
    print(f"TUNING XGBOOST: {market.upper()}")
    print("=" * 70)

    # --------------------------------------------------------
    # Load datasets
    # --------------------------------------------------------

    train_path = os.path.join(
        SPLIT_DIR,
        f"{market}_train.csv"
    )

    validation_path = os.path.join(
        SPLIT_DIR,
        f"{market}_validation.csv"
    )

    test_path = os.path.join(
        SPLIT_DIR,
        f"{market}_test.csv"
    )

    train_df = pd.read_csv(
        train_path
    )

    validation_df = pd.read_csv(
        validation_path
    )

    test_df = pd.read_csv(
        test_path
    )

    # --------------------------------------------------------
    # Features
    # --------------------------------------------------------

    feature_columns = get_feature_columns(
        train_df
    )

    X_train = train_df[
        feature_columns
    ]

    y_train = train_df[
        "target_price"
    ]

    X_validation = validation_df[
        feature_columns
    ]

    y_validation = validation_df[
        "target_price"
    ]

    X_test = test_df[
        feature_columns
    ]

    y_test = test_df[
        "target_price"
    ]

    print(
        f"\nNumber of features: {len(feature_columns)}"
    )

    print(
        f"Train: {len(train_df)}"
    )

    print(
        f"Validation: {len(validation_df)}"
    )

    print(
        f"Test: {len(test_df)}"
    )

    # ========================================================
    # TUNING
    # ========================================================

    validation_results = []

    best_model = None
    best_params = None
    best_mae = float("inf")

    print("\nStarting hyperparameter experiments...\n")

    for params in PARAMETER_CONFIGS:

        config_name = params["name"]

        print(
            f"Testing {config_name}..."
        )

        model = XGBRegressor(

            objective="reg:squarederror",

            n_estimators=params[
                "n_estimators"
            ],

            learning_rate=params[
                "learning_rate"
            ],

            max_depth=params[
                "max_depth"
            ],

            min_child_weight=params[
                "min_child_weight"
            ],

            subsample=params[
                "subsample"
            ],

            colsample_bytree=params[
                "colsample_bytree"
            ],

            reg_alpha=params[
                "reg_alpha"
            ],

            reg_lambda=params[
                "reg_lambda"
            ],

            random_state=42,

            n_jobs=-1
        )

        # ----------------------------------------------------
        # Train
        # ----------------------------------------------------

        model.fit(
            X_train,
            y_train,
            verbose=False
        )

        # ----------------------------------------------------
        # Validation prediction
        # ----------------------------------------------------

        validation_prediction = model.predict(
            X_validation
        )

        mae, rmse, mape, r2 = calculate_metrics(
            y_validation,
            validation_prediction
        )

        print(
            f"  Validation MAE  : {mae:.2f}"
        )

        print(
            f"  Validation RMSE : {rmse:.2f}"
        )

        print(
            f"  Validation MAPE : {mape:.2f}%"
        )

        print(
            f"  Validation R²   : {r2:.4f}"
        )

        validation_results.append({

            "market": market,

            "config": config_name,

            "n_estimators": params[
                "n_estimators"
            ],

            "learning_rate": params[
                "learning_rate"
            ],

            "max_depth": params[
                "max_depth"
            ],

            "min_child_weight": params[
                "min_child_weight"
            ],

            "subsample": params[
                "subsample"
            ],

            "colsample_bytree": params[
                "colsample_bytree"
            ],

            "reg_alpha": params[
                "reg_alpha"
            ],

            "reg_lambda": params[
                "reg_lambda"
            ],

            "validation_mae": mae,

            "validation_rmse": rmse,

            "validation_mape": mape,

            "validation_r2": r2
        })

        # ----------------------------------------------------
        # Check best model
        # ----------------------------------------------------

        if mae < best_mae:

            best_mae = mae

            best_model = model

            best_params = params.copy()

    # ========================================================
    # SAVE ALL VALIDATION RESULTS
    # ========================================================

    results_df = pd.DataFrame(
        validation_results
    )

    results_df = results_df.sort_values(
        "validation_mae"
    )

    results_path = os.path.join(
        OUTPUT_DIR,
        f"{market}_tuning_results.csv"
    )

    results_df.to_csv(
        results_path,
        index=False
    )

    # ========================================================
    # BEST CONFIGURATION
    # ========================================================

    print("\n")
    print("-" * 70)
    print(f"BEST CONFIGURATION: {market.upper()}")
    print("-" * 70)

    print(
        f"Configuration : {best_params['name']}"
    )

    print(
        f"Validation MAE: {best_mae:.2f}"
    )

    print("\nParameters:")

    for key, value in best_params.items():

        if key != "name":

            print(
                f"  {key}: {value}"
            )

    # ========================================================
    # TEST ONLY AFTER MODEL SELECTION
    # ========================================================

    print("\nEvaluating best model on TEST data...")

    test_prediction = best_model.predict(
        X_test
    )

    test_mae, test_rmse, test_mape, test_r2 = (
        calculate_metrics(
            y_test,
            test_prediction
        )
    )

    print("\nFinal Test Results")
    print("-" * 40)

    print(
        f"MAE  : {test_mae:.2f}"
    )

    print(
        f"RMSE : {test_rmse:.2f}"
    )

    print(
        f"MAPE : {test_mape:.2f}%"
    )

    print(
        f"R²   : {test_r2:.4f}"
    )

    # ========================================================
    # SAVE TEST PREDICTIONS
    # ========================================================

    predictions_df = test_df[
        [
            "date",
            "modal_price",
            "target_price"
        ]
    ].copy()

    predictions_df[
        "predicted_price"
    ] = test_prediction

    predictions_df[
        "error"
    ] = (
        predictions_df["target_price"]
        - predictions_df["predicted_price"]
    )

    predictions_df[
        "absolute_error"
    ] = np.abs(
        predictions_df["error"]
    )

    predictions_path = os.path.join(
        OUTPUT_DIR,
        f"{market}_test_predictions.csv"
    )

    predictions_df.to_csv(
        predictions_path,
        index=False
    )

    # ========================================================
    # SAVE BEST MODEL
    # ========================================================

    model_path = os.path.join(
        OUTPUT_DIR,
        f"{market}_best_xgboost.json"
    )

    best_model.save_model(
        model_path
    )

    # ========================================================
    # SAVE FEATURE IMPORTANCE
    # ========================================================

    importance_df = pd.DataFrame({

        "feature": feature_columns,

        "importance":
            best_model.feature_importances_
    })

    importance_df = importance_df.sort_values(
        "importance",
        ascending=False
    )

    importance_path = os.path.join(
        OUTPUT_DIR,
        f"{market}_feature_importance.csv"
    )

    importance_df.to_csv(
        importance_path,
        index=False
    )

    # ========================================================
    # RETURN FINAL RESULTS
    # ========================================================

    return {

        "market": market,

        "best_config":
            best_params["name"],

        "validation_mae":
            best_mae,

        "test_mae":
            test_mae,

        "test_rmse":
            test_rmse,

        "test_mape":
            test_mape,

        "test_r2":
            test_r2
    }


# ============================================================
# MAIN
# ============================================================

def main():

    all_results = []

    for market in MARKETS:

        try:

            result = tune_market(
                market
            )

            all_results.append(
                result
            )

        except Exception as e:

            print("\n")
            print(
                f"ERROR while tuning {market}"
            )

            print(e)

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    if all_results:

        final_df = pd.DataFrame(
            all_results
        )

        final_path = os.path.join(
            OUTPUT_DIR,
            "tuned_xgboost_results.csv"
        )

        final_df.to_csv(
            final_path,
            index=False
        )

        print("\n")
        print("=" * 70)
        print("FINAL TUNED XGBOOST RESULTS")
        print("=" * 70)

        print(
            final_df.to_string(
                index=False
            )
        )

        print(
            f"\nResults saved to:"
        )

        print(
            final_path
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()