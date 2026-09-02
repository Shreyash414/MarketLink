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

INPUT_DIR = Path(
    "data/processed/splits_v3"
)

OUTPUT_DIR = Path(
    "data/processed/models/change_xgboost_v3"
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
# COLUMNS THAT MUST NOT BE USED AS FEATURES
# ============================================================

EXCLUDED_COLUMNS = [
    "date",
    "target_price",
    "price_change",
    "price_change_pct",
    "price_direction",
    "market",
    "commodity",
    "variety",
    "grade"
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
# TRAIN ONE MARKET
# ============================================================

def train_market(market):

    print("\n")
    print("=" * 75)
    print(
        f"PRICE-CHANGE XGBOOST V3: "
        f"{market.upper()}"
    )
    print("=" * 75)

    # ========================================================
    # FILE PATHS
    # ========================================================

    train_file = (
        INPUT_DIR /
        f"{market}_train.csv"
    )

    validation_file = (
        INPUT_DIR /
        f"{market}_validation.csv"
    )

    test_file = (
        INPUT_DIR /
        f"{market}_test.csv"
    )

    # ========================================================
    # CHECK FILES
    # ========================================================

    for file_path in [
        train_file,
        validation_file,
        test_file
    ]:

        if not file_path.exists():

            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

    # ========================================================
    # LOAD DATA
    # ========================================================

    train = pd.read_csv(
        train_file
    )

    validation = pd.read_csv(
        validation_file
    )

    test = pd.read_csv(
        test_file
    )

    # ========================================================
    # DERIVE TARGET
    # ========================================================

    # V3 files contain:
    #
    # modal_price
    # target_price
    #
    # We predict:
    #
    # price_change =
    # target_price - modal_price

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
    # FEATURE COLUMNS
    # ========================================================

    feature_columns = [
        col
        for col in train.columns
        if col not in EXCLUDED_COLUMNS
    ]

    # Keep only numeric features
    feature_columns = [
        col
        for col in feature_columns
        if pd.api.types.is_numeric_dtype(
            train[col]
        )
    ]

    print(
        f"Number of features: "
        f"{len(feature_columns)}"
    )

    print("\nFeatures used:")

    for feature in feature_columns:

        print(
            f"  - {feature}"
        )

    # ========================================================
    # CHECK FOR MISSING VALUES
    # ========================================================

    missing_train = (
        train[feature_columns]
        .isna()
        .sum()
        .sum()
    )

    missing_validation = (
        validation[feature_columns]
        .isna()
        .sum()
        .sum()
    )

    missing_test = (
        test[feature_columns]
        .isna()
        .sum()
        .sum()
    )

    if (
        missing_train > 0
        or missing_validation > 0
        or missing_test > 0
    ):

        raise ValueError(
            "Missing values found in feature columns."
        )

    # ========================================================
    # X / Y
    # ========================================================

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

    # ========================================================
    # TRAIN MODEL
    # ========================================================

    model = xgb.XGBRegressor(
        **MODEL_PARAMS
    )

    print("\nTraining model...")

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

    print(
        "Training completed."
    )

    # ========================================================
    # VALIDATION PREDICTION
    # ========================================================

    validation_prediction = model.predict(
        X_validation
    )

    validation_mae = mean_absolute_error(
        y_validation,
        validation_prediction
    )

    validation_rmse = np.sqrt(
        mean_squared_error(
            y_validation,
            validation_prediction
        )
    )

    validation_r2 = r2_score(
        y_validation,
        validation_prediction
    )

    print("\nValidation Results")
    print("-" * 50)

    print(
        f"Change MAE  : "
        f"{validation_mae:.2f}"
    )

    print(
        f"Change RMSE : "
        f"{validation_rmse:.2f}"
    )

    print(
        f"Change R²   : "
        f"{validation_r2:.4f}"
    )

    # ========================================================
    # TEST PREDICTION
    # ========================================================

    predicted_change = model.predict(
        X_test
    )

    # ========================================================
    # RECONSTRUCT NEXT PRICE
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
    # FINAL PRICE METRICS
    # ========================================================

    test_price_mae = mean_absolute_error(
        actual_price,
        predicted_price
    )

    test_price_rmse = np.sqrt(
        mean_squared_error(
            actual_price,
            predicted_price
        )
    )

    test_price_r2 = r2_score(
        actual_price,
        predicted_price
    )

    print("\nFinal Test Price Results")
    print("-" * 50)

    print(
        f"MAE  : ₹{test_price_mae:.2f}"
    )

    print(
        f"RMSE : ₹{test_price_rmse:.2f}"
    )

    print(
        f"R²   : {test_price_r2:.4f}"
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

    print("\nPrice Change Prediction")
    print("-" * 50)

    print(
        f"Change MAE  : "
        f"{test_change_mae:.2f}"
    )

    print(
        f"Change RMSE : "
        f"{test_change_rmse:.2f}"
    )

    print(
        f"Direction Accuracy : "
        f"{direction_accuracy:.2f}%"
    )

    # ========================================================
    # CREATE PREDICTION DATAFRAME
    # ========================================================

    predictions = pd.DataFrame({

        "date":
            test["date"].values,

        "modal_price":
            current_price,

        "target_price":
            actual_price,

        "price_change":
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

    # ========================================================
    # SAVE PREDICTIONS
    # ========================================================

    prediction_file = (
        OUTPUT_DIR /
        f"{market}_test_predictions.csv"
    )

    predictions.to_csv(
        prediction_file,
        index=False
    )

    print("\nPredictions saved:")
    print(
        prediction_file
    )

    # ========================================================
    # FEATURE IMPORTANCE
    # ========================================================

    importance = pd.DataFrame({

        "feature":
            feature_columns,

        "importance":
            model.feature_importances_
    })

    importance = importance.sort_values(
        "importance",
        ascending=False
    )

    importance_file = (
        OUTPUT_DIR /
        f"{market}_feature_importance.csv"
    )

    importance.to_csv(
        importance_file,
        index=False
    )

    print(
        "\nFeature importance saved:"
    )

    print(
        importance_file
    )

    print("\nTop Features")
    print("-" * 50)

    print(
        importance.head(15)
        .to_string(index=False)
    )

    # ========================================================
    # SAVE MODEL
    # ========================================================

    model_file = (
        OUTPUT_DIR /
        f"{market}_change_xgboost_v3.json"
    )

    model.save_model(
        model_file
    )

    print("\nModel saved:")
    print(
        model_file
    )

    # ========================================================
    # RETURN RESULTS
    # ========================================================

    return {

        "market":
            market,

        "features":
            len(feature_columns),

        "train_rows":
            len(train),

        "validation_rows":
            len(validation),

        "test_rows":
            len(test),

        "validation_change_mae":
            validation_mae,

        "validation_change_rmse":
            validation_rmse,

        "validation_change_r2":
            validation_r2,

        "test_price_mae":
            test_price_mae,

        "test_price_rmse":
            test_price_rmse,

        "test_price_r2":
            test_price_r2,

        "test_change_mae":
            test_change_mae,

        "test_change_rmse":
            test_change_rmse,

        "direction_accuracy":
            direction_accuracy
    }


# ============================================================
# TRAIN ALL MARKETS
# ============================================================

results = []


for market in markets:

    result = train_market(
        market
    )

    results.append(
        result
    )


# ============================================================
# SAVE FINAL RESULTS
# ============================================================

results_df = pd.DataFrame(
    results
)

results_file = (
    OUTPUT_DIR /
    "change_xgboost_v3_results.csv"
)

results_df.to_csv(
    results_file,
    index=False
)


# ============================================================
# DISPLAY FINAL RESULTS
# ============================================================

print("\n")
print("=" * 75)
print("FINAL PRICE-CHANGE XGBOOST V3 RESULTS")
print("=" * 75)

print(
    results_df.to_string(
        index=False
    )
)

print("\n")
print("Results saved:")
print(
    results_file
)

print("\n")
print("=" * 75)
print("V3 TRAINING COMPLETE")
print("=" * 75)