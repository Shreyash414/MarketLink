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

SPLIT_DIR = "data/processed/change_splits"

OUTPUT_DIR = "data/processed/models/change_xgboost"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


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

        # Targets
        "next_price",
        "price_change",
        "price_change_pct",
        "price_direction",

        # Categorical
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

            features.append(
                column
            )

    return features


# ============================================================
# TRAIN ONE MARKET
# ============================================================

def train_market(market):

    print("\n" + "=" * 70)
    print(
        f"PRICE-CHANGE XGBOOST: {market.upper()}"
    )
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

    print(
        f"Train rows      : {len(train_df)}"
    )

    print(
        f"Validation rows : {len(validation_df)}"
    )

    print(
        f"Test rows       : {len(test_df)}"
    )

    # --------------------------------------------------------
    # Select features
    # --------------------------------------------------------

    feature_columns = get_feature_columns(
        train_df
    )

    print(
        f"\nNumber of features: "
        f"{len(feature_columns)}"
    )

    print("\nFeatures used:")

    for feature in feature_columns:

        print(
            f"  - {feature}"
        )

    # --------------------------------------------------------
    # X and y
    # --------------------------------------------------------

    X_train = train_df[
        feature_columns
    ]

    y_train = train_df[
        "price_change"
    ]

    X_validation = validation_df[
        feature_columns
    ]

    y_validation = validation_df[
        "price_change"
    ]

    X_test = test_df[
        feature_columns
    ]

    y_test = test_df[
        "price_change"
    ]

    # ========================================================
    # MODEL
    # ========================================================

    model = XGBRegressor(

        objective="reg:squarederror",

        n_estimators=500,

        learning_rate=0.03,

        max_depth=3,

        min_child_weight=3,

        subsample=0.8,

        colsample_bytree=0.8,

        reg_alpha=0,

        reg_lambda=1,

        random_state=42,

        n_jobs=-1
    )

    # ========================================================
    # TRAIN
    # ========================================================

    print("\nTraining model...")

    model.fit(
        X_train,
        y_train,
        verbose=False
    )

    print(
        "Training completed."
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    validation_prediction = model.predict(
        X_validation
    )

    val_mae, val_rmse, val_mape, val_r2 = (
        calculate_metrics(
            y_validation,
            validation_prediction
        )
    )

    print("\nValidation Results")
    print("-" * 40)

    print(
        f"MAE  : {val_mae:.2f}"
    )

    print(
        f"RMSE : {val_rmse:.2f}"
    )

    print(
        f"MAPE : {val_mape:.2f}%"
    )

    print(
        f"R²   : {val_r2:.4f}"
    )

    # ========================================================
    # TEST
    # ========================================================

    test_prediction_change = model.predict(
        X_test
    )

    # --------------------------------------------------------
    # Convert predicted change to predicted price
    # --------------------------------------------------------

    current_price = (
        test_df["modal_price"]
        .values
    )

    actual_next_price = (
        test_df["next_price"]
        .values
    )

    predicted_next_price = (
        current_price
        + test_prediction_change
    )

    # --------------------------------------------------------
    # Price prediction metrics
    # --------------------------------------------------------

    test_mae, test_rmse, test_mape, test_r2 = (
        calculate_metrics(
            actual_next_price,
            predicted_next_price
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
    # CHANGE PREDICTION METRICS
    # ========================================================

    change_mae = mean_absolute_error(
        y_test,
        test_prediction_change
    )

    change_rmse = np.sqrt(
        mean_squared_error(
            y_test,
            test_prediction_change
        )
    )

    print("\nPrice Change Prediction")
    print("-" * 40)

    print(
        f"Change MAE  : {change_mae:.2f}"
    )

    print(
        f"Change RMSE : {change_rmse:.2f}"
    )

    # ========================================================
    # DIRECTION ACCURACY
    # ========================================================

    actual_direction = np.sign(
        y_test.values
    )

    predicted_direction = np.sign(
        test_prediction_change
    )

    direction_accuracy = (
        np.mean(
            actual_direction
            == predicted_direction
        )
        * 100
    )

    print(
        f"Direction Accuracy : "
        f"{direction_accuracy:.2f}%"
    )

    # ========================================================
    # SAVE PREDICTIONS
    # ========================================================

    predictions_df = test_df[
        [
            "date",
            "modal_price",
            "next_price",
            "price_change"
        ]
    ].copy()

    predictions_df[
        "predicted_change"
    ] = test_prediction_change

    predictions_df[
        "predicted_price"
    ] = predicted_next_price

    predictions_df[
        "price_error"
    ] = (
        predictions_df["next_price"]
        - predictions_df["predicted_price"]
    )

    predictions_df[
        "absolute_error"
    ] = np.abs(
        predictions_df["price_error"]
    )

    predictions_df[
        "actual_direction"
    ] = np.where(
        predictions_df["price_change"] > 0,
        "up",
        np.where(
            predictions_df["price_change"] < 0,
            "down",
            "same"
        )
    )

    predictions_df[
        "predicted_direction"
    ] = np.where(
        predictions_df["predicted_change"] > 0,
        "up",
        np.where(
            predictions_df["predicted_change"] < 0,
            "down",
            "same"
        )
    )

    predictions_path = os.path.join(
        OUTPUT_DIR,
        f"{market}_test_predictions.csv"
    )

    predictions_df.to_csv(
        predictions_path,
        index=False
    )

    print(
        f"\nPredictions saved:"
    )

    print(
        predictions_path
    )

    # ========================================================
    # FEATURE IMPORTANCE
    # ========================================================

    importance_df = pd.DataFrame({

        "feature":
            feature_columns,

        "importance":
            model.feature_importances_
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

    print(
        f"Feature importance saved:"
    )

    print(
        importance_path
    )

    print("\nTop Features")
    print("-" * 40)

    print(
        importance_df
        .head(10)
        .to_string(index=False)
    )

    # ========================================================
    # SAVE MODEL
    # ========================================================

    model_path = os.path.join(
        OUTPUT_DIR,
        f"{market}_change_xgboost.json"
    )

    model.save_model(
        model_path
    )

    print(
        f"\nModel saved:"
    )

    print(
        model_path
    )

    # ========================================================
    # RETURN RESULTS
    # ========================================================

    return {

        "market":
            market,

        "validation_change_mae":
            val_mae,

        "validation_change_rmse":
            val_rmse,

        "validation_change_r2":
            val_r2,

        "test_price_mae":
            test_mae,

        "test_price_rmse":
            test_rmse,

        "test_price_mape":
            test_mape,

        "test_price_r2":
            test_r2,

        "test_change_mae":
            change_mae,

        "test_change_rmse":
            change_rmse,

        "direction_accuracy":
            direction_accuracy
    }


# ============================================================
# MAIN
# ============================================================

def main():

    all_results = []

    for market in MARKETS:

        try:

            result = train_market(
                market
            )

            all_results.append(
                result
            )

        except Exception as e:

            print("\n")
            print(
                f"ERROR while training {market}:"
            )

            print(e)

    # ========================================================
    # SAVE FINAL RESULTS
    # ========================================================

    if all_results:

        results_df = pd.DataFrame(
            all_results
        )

        results_path = os.path.join(
            OUTPUT_DIR,
            "change_xgboost_results.csv"
        )

        results_df.to_csv(
            results_path,
            index=False
        )

        print("\n")
        print("=" * 70)
        print(
            "FINAL PRICE-CHANGE XGBOOST RESULTS"
        )
        print("=" * 70)

        print(
            results_df.to_string(
                index=False
            )
        )

        print(
            f"\nResults saved:"
        )

        print(
            results_path
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()