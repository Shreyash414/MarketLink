# Task 2 — Real Potato ML Report

## 1. Objective
To build, evaluate, and validate a genuine machine learning price forecasting model for **Potato (Agra mandi, Uttar Pradesh)** using official AGMARKNET historical data, adhering strictly to a commodity-agnostic generic pipeline design with transparent validation-set feature selection and zero future data leakage.

---

## 2. Genuine Data Source
- **Platform:** data.gov.in AGMARKNET
- **Dataset Resource ID:** `35985678-0d79-46b4-9ed6-6f13308a1d24`
- **Raw History File:** `data/raw/potato_agra_history.csv`
- **Data Guard:** All proxy/relabeled CSVs were quarantined to `data/processed/_proxy_architecture_only/` and rejected during dataset loading.

---

## 3. Dataset Profile
- **File:** `data/raw/potato_agra_history.csv`
- **Total Raw Records:** 5,814
- **Unique Dates:** 5,348
- **Date Range:** 2002-11-06 to 2025-11-03
- **Data Quality Profiling Output:** Saved to `data/processed/potato_data_profile.csv`
- **Exact Duplicates:** 456
- **Missing Modal Prices:** 0
- **Invalid Price Relationships:** 0 (Min <= Modal <= Max ordering holds for all positive prices)

---

## 4. Data Quality Gate
- **Engine:** `src/data/preprocessing/quality_gate.py`
- **Quality Score:** **99.6 / 100**
- **Observed Sessions:** 2,491 (exceeds the minimum threshold of 200 sessions)
- **Quality Gate Result:** `OK` (Passed all quality checks)

---

## 5. Selected Variety and Grade
- **Selected Variety:** **Desi**
- **Selected Grade:** **FAQ**
- **Observations:** 2,491
- **Unique Sessions:** 2,491
- **Selection Rationale:** Ranked variety/grade combinations using `select_variety_grade()`. Desi/FAQ was the top-ranked combination with 2,491 clean observations (exceeding the minimum required 60 observations), covering 2011-12-10 to 2025-11-03 without corruption.

---

## 6. Feature Engineering
- **Engine:** `src/features/inference_feature_generator.py` (Generic V3 Features)
- **Features Generated:** Lags (1, 2, 3, 7, 14, 30), Rolling Means (3, 7, 14, 30), Rolling Std Devs, Momentum, Momentum %, Volatility Ratios, Price Position, Trend Strength, Calendar Sine/Cosine Encodings.
- **Data Leakage Check:** 0 NaN values, 0 infinite values, 0 future target leakage (all rolling features calculated strictly on past observations).
- **Saved Feature File:** `data/processed/features/potato_agra_features_v3.csv` (2,490 feature rows)

---

## 7. Dataset Split (Chronological)
- **Split Ratio:** 70% Train / 15% Validation / 15% Test (No random shuffling)
- **Train Set:** 1,743 rows (2011-12-10 to 2021-12-14)
- **Validation Set:** 373 rows (2021-12-15 to 2023-11-20)
- **Test Set:** 374 rows (2023-11-21 to 2025-11-03)
- **Chronological Verification:** `max(train_date) < min(val_date)` and `max(val_date) < min(test_date)` strictly satisfied.
- **Saved Splits:** `data/processed/splits_potato/train.csv`, `validation.csv`, `test.csv`

---

## 8. Baseline Results

| Baseline Model | Validation MAE | Validation RMSE | Test MAE | Test RMSE | Test MAPE |
|---|---|---|---|---|---|
| **Naive Previous-Session Price** | ₹28.32 | ₹37.15 | ₹18.58 | ₹23.46 | 1.46% |
| **7-Session Rolling Mean** | ₹31.40 | ₹40.85 | ₹19.82 | ₹24.71 | 1.55% |

---

## 9. Feature Selection (Validation Set Only)
Features were ranked by importance on Train, and candidate feature counts were evaluated on the **Validation Set ONLY** to pick the best feature subset without touching the Test set.

| Feature Count | Validation MAE (₹) | Selection Result |
|---|---|---|
| Top 5 | 28.32 | Candidate |
| Top 10 | 28.17 | Candidate |
| Top 15 | 27.52 | Candidate |
| Top 20 | 27.37 | Candidate |
| Top 30 | 27.11 | Candidate |
| Top 40 | 26.69 | Candidate |
| Top 50 | 27.39 | Candidate |
| **Top 61 (All V3)** | **26.66** | **WINNER (Best Validation MAE)** |

- **Selected Feature Count:** Top 61 features

---

## 10. Final Model Architecture
- **Model Algorithm:** XGBoost Regressor (`xgb.XGBRegressor`)
- **Hyperparameters:** `n_estimators=200`, `learning_rate=0.03`, `max_depth=4`, `subsample=0.85`, `colsample_bytree=0.85`
- **Training Data:** Combined **Train + Validation** sets (2,116 rows) using the selected 61 features.

---

## 11. Final Test Results (Evaluated ONCE on Untouched Test Set)

| Metric | Value |
|---|---|
| **Test MAE** | **₹18.50** |
| **Test RMSE** | **₹23.26** |
| **Test R²** | **0.9966** |
| **Test MAPE** | **1.44%** |
| **Direction Accuracy** | **54.0%** |

---

## 12. Baseline Comparison

- **Naive Test MAE:** ₹18.58 / quintal
- **Potato XGBoost Test MAE:** ₹18.50 / quintal
- **Improvement over Naive Baseline:** **+0.45%**

---

## 13. Error Analysis
- **Saved File:** `data/processed/models/potato/error_analysis.csv`
- **Average Test Absolute Error:** ₹18.50 / quintal
- **Overpredictions Count:** 192 (Avg error: ₹17.65)
- **Underpredictions Count:** 182 (Avg error: ₹19.40)
- **Largest Single Error:** ₹114.28 / quintal (during high volatility seasonal transition)

---

## 14. Spike Analysis
- **Training Spike Threshold:** ₹50.00 / quintal (derived from 90th percentile of Train price changes)
- **Normal Market Observations (Test):** 347 sessions
- **Normal Market Test MAE:** **₹15.74** / quintal
- **Spike Market Observations (Test):** 27 sessions (>= ₹50.00 change or >= 10% change)
- **Spike Market Test MAE:** **₹53.89** / quintal

---

## 15. Model Artifact
- **Model File:** `data/processed/models/potato/change_xgboost_v3/final/agra_final_model.json`
- **Feature File:** `data/processed/models/potato/change_xgboost_v3/final/agra_final_features.csv`

---

## 16. Model Registry
- **Catalogue File:** `data/processed/models/model_registry.json`
- **Status:** **`VALIDATED`**
- **Registered Key:** `(commodity="Potato", market="Agra")`
- **Registered Metadata:** Registered with MAE=18.50, RMSE=23.26, R²=0.9966, Direction Accuracy=54.0%, Variety=Desi, Grade=FAQ.

---

## 17. Inference Validation
- Verified `ModelPredictor.predict_next_price(commodity="Potato", market="Agra", ...)` loads the genuine Potato model and outputs valid price forecasts (`predicted_price = ₹1254.58` from `current_price = ₹1250.00`).
- Verified `RiskEngine.evaluate_risk_and_confidence(...)` computes valid confidence scores (77.6/100, `LOW` risk).
- Verified `MandiRecommender` executes end-to-end for Potato.

---

## 18. Test Suite Execution
- **Command:** `python -m unittest discover -s tests -p "test_*.py"`
- **Result:** **`Ran 35 tests in 70.832s — OK`** (0 failures, 0 skipped).

---

## 19. Final Status
**`VALIDATED`**

---

## 20. Next Task
**Next task: Real Tomato ML training and validation.**
