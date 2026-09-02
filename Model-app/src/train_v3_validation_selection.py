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

OUTPUT_DIR = (
    MODEL_DIR /
    "validation_selection"
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
# FEATURE COUNTS
# ============================================================

TOP_K_VALUES = [
    5,
    10,
    15,
    20,
    30,
    40,
    50,
    61
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
# GET TOP K FEATURES
# ============================================================

def get_features(market, k):

    importance_file = (
        MODEL_DIR /
        f"{market}_feature_importance.csv"
    )

    if not importance_file.exists():

        raise FileNotFoundError(
            f"Feature importance file not found:\n"
            f"{importance_file}"
        )

    importance = pd.read_csv(
        importance_file
    )

    # Sort from most important to least important
    importance = importance.sort_values(
        "importance",
        ascending=False
    ).reset_index(drop=True)

    total_features = len(importance)

    if k > total_features:

        raise ValueError(
            f"{market}: requested Top {k}, "
            f"but only {total_features} "
            f"features are available."
        )

    return (
        importance
        .head(k)["feature"]
        .tolist()
    )


# ============================================================
# ADD TARGET
# ============================================================

def add_target(df):

    df = df.copy()

    df["price_change"] = (
        df["target_price"]
        - df["modal_price"]
    )

    return df


# ============================================================
# TRAIN ONE MODEL
# ============================================================

def train_model(
    X_train,
    y_train,
    X_validation,
    y_validation
):

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

    return model


# ============================================================
# MAIN
# ============================================================

all_results = []


for market in MARKETS:

    print("\n")
    print("=" * 80)
    print(
        f"VALIDATION FEATURE SELECTION: "
        f"{market.upper()}"
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

    train = add_target(train)

    validation = add_target(
        validation
    )

    test = add_target(
        test
    )

    # ========================================================
    # TEST DIFFERENT FEATURE COUNTS
    # ========================================================

    for k in TOP_K_VALUES:

        print("\n")
        print(
            f"{market.upper()} → TOP {k}"
        )
        print("-" * 60)

        # ----------------------------------------------------
        # GET TOP K FEATURES DIRECTLY
        # ----------------------------------------------------

        feature_columns = get_features(
            market,
            k
        )

        # ----------------------------------------------------
        # SAFETY CHECK
        # ----------------------------------------------------

        missing_features = [

            feature

            for feature in feature_columns

            if feature not in train.columns
        ]

        if missing_features:

            raise ValueError(
                f"Missing features:\n"
                f"{missing_features}"
            )

        # ----------------------------------------------------
        # CREATE TRAINING DATA
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # TRAIN
        # ----------------------------------------------------

        model = train_model(
            X_train,
            y_train,
            X_validation,
            y_validation
        )

        # ----------------------------------------------------
        # VALIDATION PREDICTION
        # ----------------------------------------------------

        predicted_change = model.predict(
            X_validation
        )

        # ----------------------------------------------------
        # CHANGE METRICS
        # ----------------------------------------------------

        validation_change_mae = (
            mean_absolute_error(
                y_validation,
                predicted_change
            )
        )

        validation_change_rmse = np.sqrt(
            mean_squared_error(
                y_validation,
                predicted_change
            )
        )

        validation_change_r2 = (
            r2_score(
                y_validation,
                predicted_change
            )
        )

        # ----------------------------------------------------
        # RECONSTRUCT PRICE
        # ----------------------------------------------------

        current_price = (
            validation[
                "modal_price"
            ].to_numpy()
        )

        actual_price = (
            validation[
                "target_price"
            ].to_numpy()
        )

        predicted_price = (
            current_price
            + predicted_change
        )

        # ----------------------------------------------------
        # PRICE METRICS
        # ----------------------------------------------------

        validation_price_mae = (
            mean_absolute_error(
                actual_price,
                predicted_price
            )
        )

        validation_price_rmse = np.sqrt(
            mean_squared_error(
                actual_price,
                predicted_price
            )
        )

        validation_price_r2 = (
            r2_score(
                actual_price,
                predicted_price
            )
        )

        # ----------------------------------------------------
        # DIRECTION
        # ----------------------------------------------------

        actual_direction = np.sign(
            y_validation.to_numpy()
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

        # ----------------------------------------------------
        # STORE RESULTS
        # ----------------------------------------------------

        all_results.append({

            "market":
                market,

            "top_k":
                k,

            "validation_change_mae":
                validation_change_mae,

            "validation_change_rmse":
                validation_change_rmse,

            "validation_change_r2":
                validation_change_r2,

            "validation_price_mae":
                validation_price_mae,

            "validation_price_rmse":
                validation_price_rmse,

            "validation_price_r2":
                validation_price_r2,

            "validation_direction_accuracy":
                direction_accuracy
        })

        # ----------------------------------------------------
        # PRINT
        # ----------------------------------------------------

        print(
            f"Validation Change MAE : "
            f"{validation_change_mae:.2f}"
        )

        print(
            f"Validation Price MAE  : "
            f"₹{validation_price_mae:.2f}"
        )

        print(
            f"Validation Price RMSE : "
            f"₹{validation_price_rmse:.2f}"
        )

        print(
            f"Validation Price R²   : "
            f"{validation_price_r2:.4f}"
        )

        print(
            f"Direction Accuracy    : "
            f"{direction_accuracy:.2f}%"
        )


# ============================================================
# RESULTS DATAFRAME
# ============================================================

results_df = pd.DataFrame(
    all_results
)


# ============================================================
# SAVE ALL RESULTS
# ============================================================

results_file = (
    OUTPUT_DIR /
    "validation_feature_selection_results.csv"
)

results_df.to_csv(
    results_file,
    index=False
)


# ============================================================
# SELECT BEST USING VALIDATION PRICE MAE
# ============================================================

best_rows = []

for market in MARKETS:

    market_results = (
        results_df[
            results_df["market"]
            == market
        ]
    )

    best = (
        market_results
        .sort_values(
            "validation_price_mae"
        )
        .iloc[0]
    )

    best_rows.append(
        best
    )


best_df = pd.DataFrame(
    best_rows
)


# ============================================================
# SAVE BEST CONFIGURATION
# ============================================================

best_file = (
    OUTPUT_DIR /
    "best_validation_feature_configuration.csv"
)

best_df.to_csv(
    best_file,
    index=False
)


# ============================================================
# PRINT COMPLETE RESULTS
# ============================================================

print("\n")
print("=" * 80)
print(
    "VALIDATION FEATURE SELECTION RESULTS"
)
print("=" * 80)

print(
    results_df.to_string(
        index=False
    )
)


# ============================================================
# PRINT WINNERS
# ============================================================

print("\n")
print("=" * 80)
print(
    "BEST FEATURE COUNT"
)
print(
    "(SELECTED USING VALIDATION PRICE MAE ONLY)"
)
print("=" * 80)


for _, row in best_df.iterrows():

    print("\n")

    print(
        f"Market              : "
        f"{row['market'].upper()}"
    )

    print(
        f"Best feature count  : "
        f"{int(row['top_k'])}"
    )

    print(
        f"Validation Price MAE: "
        f"₹{row['validation_price_mae']:.2f}"
    )

    print(
        f"Validation Price RMSE:"
        f" ₹{row['validation_price_rmse']:.2f}"
    )

    print(
        f"Validation Price R²  : "
        f"{row['validation_price_r2']:.4f}"
    )

    print(
        f"Direction Accuracy   : "
        f"{row['validation_direction_accuracy']:.2f}%"
    )


# ============================================================
# FILE LOCATIONS
# ============================================================

print("\n")
print("=" * 80)

print(
    "All results saved to:"
)

print(
    results_file
)

print("\n")

print(
    "Best configurations saved to:"
)

print(
    best_file
)

print("\n")
print("=" * 80)
print(
    "VALIDATION FEATURE SELECTION COMPLETE"
)
print("=" * 80)