import os
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib


# ============================================================
# CONFIGURATION
# ============================================================

MARKETS = ["bareilly", "bargarh", "nagpur"]

SPLIT_DIR = "data/processed/splits"
MODEL_DIR = "data/processed/models/xgboost"

os.makedirs(MODEL_DIR, exist_ok=True)


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(y_true, y_pred):
    """
    Calculate regression metrics.
    """

    mae = mean_absolute_error(y_true, y_pred)

    rmse = np.sqrt(
        mean_squared_error(y_true, y_pred)
    )

    # Avoid division by zero in MAPE
    non_zero = y_true != 0

    if non_zero.sum() > 0:
        mape = np.mean(
            np.abs(
                (y_true[non_zero] - y_pred[non_zero])
                / y_true[non_zero]
            )
        ) * 100
    else:
        mape = np.nan

    r2 = r2_score(y_true, y_pred)

    return mae, rmse, mape, r2


# ============================================================
# FEATURE SELECTION
# ============================================================

def get_feature_columns(df):
    """
    Select numerical features for XGBoost.

    We exclude:
    - date
    - target_price
    - categorical columns
    """

    excluded_columns = [
        "date",
        "target_price",
        "market",
        "commodity",
        "variety",
        "grade"
    ]

    features = [
        column
        for column in df.columns
        if column not in excluded_columns
        and pd.api.types.is_numeric_dtype(df[column])
    ]

    return features


# ============================================================
# TRAIN ONE MARKET
# ============================================================

def train_market(market):

    print("\n" + "=" * 70)
    print(f"TRAINING XGBOOST MODEL: {market.upper()}")
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

    train_df = pd.read_csv(train_path)
    validation_df = pd.read_csv(validation_path)
    test_df = pd.read_csv(test_path)

    print(f"Train rows      : {len(train_df)}")
    print(f"Validation rows : {len(validation_df)}")
    print(f"Test rows       : {len(test_df)}")

    # --------------------------------------------------------
    # Select features
    # --------------------------------------------------------

    feature_columns = get_feature_columns(train_df)

    print("\nFeatures used:")
    for feature in feature_columns:
        print(f"  - {feature}")

    X_train = train_df[feature_columns]
    y_train = train_df["target_price"]

    X_validation = validation_df[feature_columns]
    y_validation = validation_df["target_price"]

    X_test = test_df[feature_columns]
    y_test = test_df["target_price"]

    # --------------------------------------------------------
    # Create XGBoost model
    # --------------------------------------------------------

    model = XGBRegressor(
        objective="reg:squarederror",

        n_estimators=500,

        learning_rate=0.03,

        max_depth=6,

        min_child_weight=3,

        subsample=0.8,

        colsample_bytree=0.8,

        reg_alpha=0.0,

        reg_lambda=1.0,

        random_state=42,

        n_jobs=-1
    )

    # --------------------------------------------------------
    # Train
    # --------------------------------------------------------

    print("\nTraining model...")

    model.fit(
        X_train,
        y_train,
        verbose=False
    )

    print("Training completed.")

    # ========================================================
    # VALIDATION PREDICTION
    # ========================================================

    validation_predictions = model.predict(
        X_validation
    )

    val_mae, val_rmse, val_mape, val_r2 = calculate_metrics(
        y_validation,
        validation_predictions
    )

    print("\nValidation Results")
    print("-" * 40)
    print(f"MAE  : {val_mae:.2f}")
    print(f"RMSE : {val_rmse:.2f}")
    print(f"MAPE : {val_mape:.2f}%")
    print(f"R²   : {val_r2:.4f}")

    # ========================================================
    # TEST PREDICTION
    # ========================================================

    test_predictions = model.predict(
        X_test
    )

    test_mae, test_rmse, test_mape, test_r2 = calculate_metrics(
        y_test,
        test_predictions
    )

    print("\nTest Results")
    print("-" * 40)
    print(f"MAE  : {test_mae:.2f}")
    print(f"RMSE : {test_rmse:.2f}")
    print(f"MAPE : {test_mape:.2f}%")
    print(f"R²   : {test_r2:.4f}")

    # ========================================================
    # SAVE TEST PREDICTIONS
    # ========================================================

    predictions_df = test_df[
        ["date", "modal_price", "target_price"]
    ].copy()

    predictions_df["predicted_price"] = test_predictions

    predictions_df["error"] = (
        predictions_df["target_price"]
        - predictions_df["predicted_price"]
    )

    predictions_df["absolute_error"] = np.abs(
        predictions_df["error"]
    )

    predictions_path = os.path.join(
        MODEL_DIR,
        f"{market}_test_predictions.csv"
    )

    predictions_df.to_csv(
        predictions_path,
        index=False
    )

    print(
        f"\nTest predictions saved: {predictions_path}"
    )

    # ========================================================
    # SAVE VALIDATION PREDICTIONS
    # ========================================================

    validation_predictions_df = validation_df[
        ["date", "modal_price", "target_price"]
    ].copy()

    validation_predictions_df["predicted_price"] = (
        validation_predictions
    )

    validation_predictions_path = os.path.join(
        MODEL_DIR,
        f"{market}_validation_predictions.csv"
    )

    validation_predictions_df.to_csv(
        validation_predictions_path,
        index=False
    )

    # ========================================================
    # FEATURE IMPORTANCE
    # ========================================================

    importance_df = pd.DataFrame({
        "feature": feature_columns,
        "importance": model.feature_importances_
    })

    importance_df = importance_df.sort_values(
        "importance",
        ascending=False
    )

    importance_path = os.path.join(
        MODEL_DIR,
        f"{market}_feature_importance.csv"
    )

    importance_df.to_csv(
        importance_path,
        index=False
    )

    print(
        f"Feature importance saved: {importance_path}"
    )

    # Show top features

    print("\nTop Features")
    print("-" * 40)

    print(
        importance_df.head(10).to_string(index=False)
    )

    # ========================================================
    # SAVE MODEL
    # ========================================================

    model_path = os.path.join(
        MODEL_DIR,
        f"{market}_xgboost.pkl"
    )

    joblib.dump(
        model,
        model_path
    )

    print(
        f"\nModel saved: {model_path}"
    )

    # ========================================================
    # RETURN RESULTS
    # ========================================================

    return {
        "market": market,

        "train_rows": len(train_df),
        "validation_rows": len(validation_df),
        "test_rows": len(test_df),

        "validation_mae": val_mae,
        "validation_rmse": val_rmse,
        "validation_mape": val_mape,
        "validation_r2": val_r2,

        "test_mae": test_mae,
        "test_rmse": test_rmse,
        "test_mape": test_mape,
        "test_r2": test_r2
    }


# ============================================================
# MAIN
# ============================================================

def main():

    all_results = []

    for market in MARKETS:

        try:

            result = train_market(market)

            all_results.append(result)

        except Exception as e:

            print(
                f"\nERROR while training {market}:"
            )

            print(e)

    # ========================================================
    # SAVE ALL RESULTS
    # ========================================================

    if all_results:

        results_df = pd.DataFrame(
            all_results
        )

        results_path = os.path.join(
            MODEL_DIR,
            "xgboost_results.csv"
        )

        results_df.to_csv(
            results_path,
            index=False
        )

        print("\n" + "=" * 70)
        print("FINAL XGBOOST RESULTS")
        print("=" * 70)

        print(
            results_df.to_string(index=False)
        )

        print(
            f"\nResults saved: {results_path}"
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()