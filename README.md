# SIH26132 — AI-Powered Mandi Recommendation System for Farmers

A smart agricultural mandi recommendation and price forecasting engine built for Smart India Hackathon (SIH26132).

---

## 🌟 Overview

The **SIH26132 Mandi Recommendation System** assists farmers in selecting the most profitable market (mandi) for selling their agricultural produce. Rather than recommending markets solely based on the highest forecasted price, the system evaluates:
1. **Predicted Modal Price & Price Change Trend** (using XGBoost V3 time-series models)
2. **Transportation Cost Tariff** (configurable ₹/quintal/km based on Haversine distance)
3. **Market Transaction Fees** (₹/quintal)
4. **Market Risk & Volatility Assessment** (detecting price spikes and historical volatility)
5. **Transparent Prediction Confidence** (formulaic score out of 100 based on model error and data recency)
6. **Expected Net Return** (Primary economic ranking metric)

The current implementation provides a validated, production-ready pipeline for **Onion**, architected modularly for generalization across **~226 commodities**.

---

## 🏗️ System Architecture

### Current (Historical ML Research & Validation Pipeline)
```
Historical CSVs
  └─> Data Cleaning & Validation (create_model_datasets.py)
       └─> Feature Engineering Base + V3 (create_features_v3.py)
            └─> Time-Series Split (split_features_v3.py)
                 └─> Feature Selection (Top 5 / 20 / 50 V3 features)
                      └─> Trained XGBoost Models (train_final_price_model.py)
                           └─> Static Test Set Predictions
```

### Target (Live Production & Application Pipeline)
```
AGMARKNET API (data.gov.in)
  ├─> Retries (Exponential Backoff) & Timeout Controls
  ├─> Local File Cache (data/cache/current_onion_cache.csv)
  └─> Automatic Cache Fallback (Source: LIVE vs CACHE)
       │
       ▼
Recent History + Current Data Merging
  ├─> Chronological Sorting & Deduplication
  └─> Preserves Observed Market Sessions (No Fake Calendar Days)
       │
       ▼
Dynamic V3 Feature Engineering (Inference Mode)
  └─> Computes Exact Features for Latest Market Session
       │
       ▼
Pre-Trained V3 XGBoost Inference (Separate from Training)
  └─> Loads {market}_final_model.json & {market}_final_features.csv
       │
       ▼
Risk Assessment & Transparent Confidence Engine
  ├─> Spike Detection & Volatility Thresholding
  └─> Transparent Confidence Score (0-100 based on MAE, Volatility, Data Recency)
       │
       ▼
Farmer Input & Geo-Discovery
  ├─> Farmer GPS (lat, lon), Quantity (quintals), Commodity ("Onion")
  └─> Haversine Distance & Nearby Eligible Mandi Filtering
       │
       ▼
Economics & Transport Cost Engine
  ├─> Configurable Tariff (default ₹3/quintal/km) & Market Fee (₹20/quintal)
  ├─> Gross Revenue = Predicted Price × Quantity
  └─> Net Return = Gross Revenue - Transport Cost - Market Fee
       │
       ▼
Mandi Ranking & Recommendation Generator
  ├─> Primary Metric: Expected Net Return (descending)
  └─> Exposes Net Return, Distance, Risk, Confidence & Warning Reasons
       │
       ▼
Structured Output Contract (JSON / Dataclass)
  └─> Ready for future LLM / Ollama Natural Language Explanations
```

---

## 📂 Repository Structure

```
SIH26132/
├── src/
│   ├── config/              # Centralized configuration & settings
│   │   ├── config.py
│   │   └── __init__.py
│   ├── data/
│   │   ├── data_reliability.py   # Real-time data freshness, price validation & warm-up sufficiency
│   │   ├── ingestion/       # API data fetching, retries, caching, fallback
│   │   │   └── current_data_fetcher.py
│   │   └── preprocessing/   # Historical data loading & merging
│   │       └── historical_merger.py
│   ├── features/            # Dynamic V3 feature engineering for inference
│   │   └── inference_feature_generator.py
│   ├── models/              # Pre-trained model loading, quality gating & price forecasting
│   │   ├── model_predictor.py
│   │   └── model_quality_gate.py
│   ├── risk/                # Spike detection, volatility analysis & confidence scoring
│   │   └── risk_engine.py

│   ├── contracts/           # Production inference response contract & validation
│   │   └── inference_contract.py
│   ├── recommendation/      # Core recommendation engine & output schemas
│   │   ├── mandi_recommender.py
│   │   └── schemas.py

│   ├── utils/               # Logger & geographic utilities
│   │   ├── logger.py
│   │   └── geo_utils.py
│   ├── fetch_current_onion.py # Ingestion CLI wrapper
│   └── recommend_mandi.py     # Mandi recommendation CLI entry point
│
├── data/
│   ├── raw/                 # Raw market history CSVs
│   ├── processed/           # Cleaned datasets & pre-trained XGBoost V3 models
│   │   └── models/change_xgboost_v3/final/
│   └── cache/               # Local cache for API responses
│
├── tests/                   # Unit and integration test suite
│   ├── test_haversine.py
│   ├── test_economics.py
│   ├── test_risk_confidence.py
│   ├── test_data_ingestion.py
│   └── test_inference_pipeline.py
│
├── .env                     # Environment variables (API Key - DO NOT COMMIT)
├── .gitignore               # Git ignore file
└── README.md                # System documentation
```

---

## 🔑 Environment Setup & API Configuration

1. **Prerequisites:** Python 3.9+
2. **Environment Variables:** Create a `.env` file in the project root directory containing your `DATA_GOV_API_KEY`:

```env
DATA_GOV_API_KEY=your_ogd_api_key_here
```

> [!CAUTION]
> Never hard-code, log, print, or commit the `DATA_GOV_API_KEY` or `.env` file.

---

## 🚀 Running the Onion Pipeline

### 1. Fetch Current Market Data
Runs the production ingestion engine with exponential backoff retries, local caching, and fallback:

```powershell
python src/fetch_current_onion.py
```

### 2. Generate Farmer Mandi Recommendation
Run recommendation engine with example farmer inputs:

```powershell
python src/recommend_mandi.py
```

### Python API Usage Example:

```python
from src.recommendation import recommend_mandi

# Farmer near Delhi (28.6139, 77.2090) selling 20 quintals of Onion
result = recommend_mandi(
    farmer_latitude=28.6139,
    farmer_longitude=77.2090,
    quantity_quintals=20.0,
    commodity="Onion",
    max_distance_km=500.0,
    transport_rate=3.0
)

# Returns pandas DataFrame or structured RecommendationResult dataclass
print(result)
```

---

## 🧪 Running Tests

Execute the unit and integration test suite:

```powershell
python -m unittest tests/test_haversine.py tests/test_economics.py tests/test_risk_confidence.py tests/test_data_ingestion.py tests/test_inference_pipeline.py
```

---

## 📊 Economics & Confidence Formulas

### 1. Economics Formula
$$\text{Transport Cost} = \text{Distance (km)} \times \text{Tariff Rate (₹/quintal/km)} \times \text{Quantity (quintals)}$$

$$\text{Market Fee} = \text{Fee Rate (₹/quintal)} \times \text{Quantity (quintals)}$$

$$\text{Gross Revenue} = \text{Predicted Price (₹/quintal)} \times \text{Quantity (quintals)}$$

$$\text{Expected Net Return} = \text{Gross Revenue} - \text{Transport Cost} - \text{Market Fee}$$

### 2. Transparent Confidence Score Formula (0 - 100)
$$\text{Confidence Score} = 100 \times \left(1 - \frac{\text{Historical Model MAE}}{\text{Current Price}}\right) - (\text{Volatility Ratio} \times 40) - \text{Spike Penalty} - \text{Recency Penalty}$$

---

## 📚 Documentation & Integration Reports

- [docs/FINAL_AI_ML_PRODUCTION_READINESS_REPORT.md](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/docs/FINAL_AI_ML_PRODUCTION_READINESS_REPORT.md) — Final AI/ML Production Readiness Report
- [docs/AI_ML_BACKEND_HANDOFF.md](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/docs/AI_ML_BACKEND_HANDOFF.md) — Backend Developer Handoff Guide
- [docs/AI_INFERENCE_CONTRACT.md](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/docs/AI_INFERENCE_CONTRACT.md) — Production AI Inference Contract Specification
- [docs/TASK_6_MULTI_COMMODITY_MODEL_QUALITY_REPORT.md](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/docs/TASK_6_MULTI_COMMODITY_MODEL_QUALITY_REPORT.md) — Multi-Commodity Model Quality Audit Report
- `WHAT_IS_DONE.md` — Honest status of real vs proxy ML work
- `AI_ML_AUDIT.md` — Component classification matrix & hardcoding audit
- `PROJECT_TASK_LOG.md` — Complete project task log