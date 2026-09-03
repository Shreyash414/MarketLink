# SIH26132 — Complete AI/ML Mandi Recommendation System Documentation

**Project Name:** AI-Powered Mandi Recommendation & Price Forecasting Engine  
**Hackathon Target:** Smart India Hackathon (SIH26132)  
**System Status:** `PRODUCTION_READY_WITH_WARNINGS`  
**Test Suite:** 101/101 Tests Passing (100%)  
**Contract Version:** `1.0.0`

---

## 📖 Table of Contents
1. [Executive Overview & Problem Statement](#1-executive-overview--problem-statement)
2. [End-to-End System Architecture & How It Works](#2-end-to-end-system-architecture--how-it-works)
3. [Core Subsystems & Module Breakdown](#3-core-subsystems--module-breakdown)
4. [Data Provenance & Model Portfolio](#4-data-provenance--model-portfolio)
5. [Phase-by-Phase Development History (Tasks 1–10)](#5-phase-by-phase-development-history-tasks-110)
6. [Safety & Quality Gating Architecture](#6-safety--quality-gating-architecture)
7. [Economic & Confidence Formulas](#7-economic--confidence-formulas)
8. [Canonical API Integration Contract](#8-canonical-api-integration-contract)
9. [Test Suite & Verification Commands](#9-test-suite--verification-commands)
10. [Developer & Teammate Integration Guide](#10-developer--teammate-integration-guide)

---

## 1. Executive Overview & Problem Statement

Farmers across India often face severe income loss when selling their agricultural produce at local mandis (wholesale markets). Traditional decisions are made based purely on proximity or word-of-mouth price rumors, ignoring:
- **Transport logistics cost** to alternative markets.
- **Short-term price volatility** and unexpected price drops.
- **Market transaction fees** and spatial price differentials.
- **Historical model accuracy & data freshness**.

The **SIH26132 Mandi Recommendation System** solves this problem by serving as an intelligent, data-driven advisor. Instead of blindly recommending the mandi with the highest price forecast, it evaluates:
1. **Predicted Modal Price** (via XGBoost V3 time-series change models).
2. **Transportation Cost** (Haversine distance $\times$ configurable tariff ₹/quintal/km).
3. **Market Transaction Fees** (₹/quintal).
4. **Expected Net Return** (Primary economic ranking metric: $\text{Gross Revenue} - \text{Transport Cost} - \text{Market Fee}$).
5. **Dual Safety Gates** (Data freshness validation & Model quality gating).
6. **Transparent Confidence Score** (0–100 score based on error percentiles, volatility, and data age).

The system is fully commodity-agnostic and currently validated across **5 major commodities (Potato, Tomato, Wheat, Onion, Rice)** with pre-trained models across multiple mandis.

---

## 2. End-to-End System Architecture & How It Works

The recommendation pipeline follows a strict, deterministic 10-step sequence from farmer request input to JSON inference output:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. FARMER INPUT REQUEST                                                         │
│    Commodity (e.g. Potato), GPS (lat=27.1767, lon=78.0081), Quantity (10 quintals)│
└────────────────────────┬────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. LIVE DATA FETCHING & CACHE FALLBACK (src/data/ingestion/current_data_fetcher)│
│    Fetches AGMARKNET live market data via API; fails fast to local CSV cache.   │
└────────────────────────┬────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. TASK 8 DATA RELIABILITY GATE (src/data/data_reliability.py)                  │
│    Checks: non-negative prices, numeric sanity, chronological order,             │
│    warm-up session history >= 31. Tags data: LIVE_FRESH / CACHE_FRESH / CACHE_STALE.│
└────────────────────────┬────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. HISTORICAL MERGING (src/data/preprocessing/historical_merger.py)             │
│    Merges current market record with historical session series.                 │
│    Deduplicates and preserves observed trading sessions (no fake calendar padding).│
└────────────────────────┬────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. DYNAMIC V3 FEATURE GENERATION (src/features/inference_feature_generator.py) │
│    Computes 1-30d price lags, rolling 7-30d mean/std/min/max, momentum & trends.│
└────────────────────────┬────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 6. TASK 7 MODEL QUALITY GATE (src/models/model_quality_gate.py)                 │
│    Consults model_registry.json. Checks usage status:                           │
│    - PRODUCTION_READY: Allowed                                                  │
│    - USABLE_WITH_WARNING: Allowed with warning badge                             │
│    - DISABLED / RESEARCH_ONLY / MISSING: BLOCKED (Skipped for farmers)          │
└────────────────────────┬────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 7. PRE-TRAINED XGBOOST INFERENCE (src/models/model_predictor.py)                │
│    Loads {market}_final_model.json. Predicts price change ΔP.                    │
│    Final Predicted Price = Latest Modal Price + ΔP                               │
└────────────────────────┬────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 8. RISK ASSESSMENT & CONFIDENCE ENGINE (src/risk/risk_engine.py)               │
│    Computes spike detection, volatility risk levels (LOW/MEDIUM/HIGH), 80%/95%  │
│    empirical prediction intervals, and transparent 0-100 confidence score.     │
└────────────────────────┬────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 9. TRANSPORT ECONOMICS ENGINE (src/economics/economics_engine.py)              │
│    Haversine distance (km) -> Transport Cost = distance * rate * quantity.      │
│    Market Fee = fee * quantity. Net Return = Gross Revenue - Total Cost.        │
│    Ranks eligible mandis by Expected Net Return (descending).                    │
└────────────────────────┬────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 10. TASK 9 CANONICAL INFERENCE CONTRACT (src/contracts/inference_contract.py)  │
│    Validates status enums, price non-negativity, score bounds [0, 100].         │
│    Generates stable, versioned (v1.0.0) JSON response for backend API service. │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Subsystems & Module Breakdown

| Module Path | Purpose & Responsibilities | Key Functions / Classes |
|---|---|---|
| [`src/contracts/inference_contract.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/contracts/inference_contract.py) | Defines versioned JSON integration contract, metadata, canonical dataclasses, validation rules, and JSON serialization. | `CanonicalRecommendationResponse`, `CanonicalInferenceItem`, `validate_inference_contract()`, `build_canonical_recommendation()` |
| [`src/recommendation/mandi_recommender.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/recommendation/mandi_recommender.py) | End-to-end recommendation orchestrator integrating data ingestion, safety gates, ML inference, economics, and mandi ranking. | `MandiRecommender`, `recommend_mandi()`, `recommend_canonical()` |
| [`src/recommendation/schemas.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/recommendation/schemas.py) | Internal dataclass contracts for recommendations. | `MandiRecommendationItem`, `RecommendationResult` |
| [`src/models/model_quality_gate.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/models/model_quality_gate.py) | Task 7 centralized gating layer enforcing production safety rules based on measured model accuracy. | `get_model_quality_metadata()`, `can_use_model()`, `evaluate_model_gating()` |
| [`src/data/data_reliability.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/data/data_reliability.py) | Task 8 centralized data freshness and price validation layer. Rejects malformed rows and enforces warm-up history. | `DataReliabilityResult`, `evaluate_data_freshness()`, `validate_price_data()`, `evaluate_historical_sufficiency()`, `evaluate_data_reliability()` |
| [`src/models/model_predictor.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/models/model_predictor.py) | Pre-trained XGBoost V3 inference engine. Calculates price change forecasts dynamically. | `ModelPredictor`, `predict_next_price()`, `PredictionOutput` |
| [`src/features/inference_feature_generator.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/features/inference_feature_generator.py) | Dynamic time-series feature engineering in inference mode without target leakage. | `generate_v3_features()`, `prepare_inference_features()` |
| [`src/risk/risk_engine.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/risk/risk_engine.py) | Price spike detection, historical volatility analysis, empirical prediction intervals, and transparent confidence scoring. | `calculate_transparent_confidence()`, `calculate_prediction_interval()` |
| [`src/economics/economics_engine.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/economics/economics_engine.py) | Transport cost calculation, market fee calculation, gross revenue, net return, and mandi ranking logic. | `calculate_transport_cost()`, `calculate_net_return()`, `rank_mandis()` |
| [`src/utils/geo_utils.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/utils/geo_utils.py) | Pure mathematical geospatial distance module using Haversine formula. | `haversine_distance()`, `calculate_distance_matrix()` |
| [`src/data/ingestion/current_data_fetcher.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/data/ingestion/current_data_fetcher.py) | AGMARKNET API live data fetcher with retries, timeout controls, circuit breakers, and local CSV cache fallback. | `CurrentDataFetcher`, `fetch_current_data()` |
| [`src/data/preprocessing/historical_merger.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/data/preprocessing/historical_merger.py) | Merges live/cache data with historical series, chronologically sorting and deduplicating. | `merge_current_with_history()` |
| [`src/config/commodity_registry.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/config/commodity_registry.py) | Central commodity registry managing commodity codes, market lists, and default economic tariffs. | `CommodityRegistry`, `get_commodity_config()` |
| [`src/config/model_registry.py`](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/src/config/model_registry.py) | Catalogue persistence for model usage status and reliability scores (`model_registry.json`). | `ModelRegistry`, `get_registered_model()` |

---

## 4. Data Provenance & Model Portfolio

All production models currently enabled for farmer-facing inference originate from **genuine official historical data** acquired from AGMARKNET / `data.gov.in`.

### Verified Production Model Portfolio:

| Commodity | Mandi | Historical Source | Date Range | Sessions | Model Status | Reliability Score (0-100) | Quality Class | Recommendation Action |
|---|---|---|---|---|---|---|---|---|
| **Potato** | Agra | AGMARKNET Official API | 2011-12-10 to 2025-11-03 | 2,491 | `PRODUCTION_READY` | **69.7** | `STRONG` | Allowed (Farmer-Facing) |
| **Tomato** | Kolar | AGMARKNET Official API | 2008-01-01 to 2025-11-03 | 4,770 | `PRODUCTION_READY` | **65.0** | `STRONG` | Allowed (Farmer-Facing) |
| **Onion** | Bareilly | AGMARKNET Historical | 2008-01-01 to 2025-01-25 | 3,627 | `USABLE_WITH_WARNING` | **48.7** | `ACCEPTABLE` | Allowed with Warning Badge |
| **Onion** | Bargarh | AGMARKNET Historical | 2005-03-01 to 2025-01-25 | 4,256 | `USABLE_WITH_WARNING` | **45.4** | `ACCEPTABLE` | Allowed with Warning Badge |
| **Wheat** | Indore | AGMARKNET Official API | 2014-07-14 to 2025-04-29 | 2,153 | `USABLE_WITH_WARNING` | **38.6** | `ACCEPTABLE` | Allowed with Warning Badge |
| **Onion** | Nagpur | AGMARKNET Historical | 2001-05-26 to 2025-01-25 | 4,167 | `DISABLED` | **35.0** | `REJECT` | **BLOCKED** (Task 7 Gate) |
| **Wheat** | Khanna | AGMARKNET Official API | 2007-06-02 to 2024-10-01 | 1,176 | `DISABLED` | **19.4** | `REJECT` | **BLOCKED** (Task 7 Gate) |
| **Rice** | Burdwan | AGMARKNET Official API | 2002-11-25 to 2012-09-19 | 2,346 | `DISABLED` | **7.0** | `REJECT` | **BLOCKED** (Task 7 Gate) |

> [!IMPORTANT]
> **Proxy Data Quarantine:** All obsolete proxy CSV files (`potato_agra_model.csv`, `tomato_kolar_model.csv`, `wheat_khanna_model.csv`, `rice_burdwan_model.csv`) are quarantined under `data/processed/_proxy_architecture_only/`. They cannot enter production pipelines.

---

## 5. Phase-by-Phase Development History (Tasks 1–10)

### Phase 1–5: Core Engine Prototype & Onion Foundation
- Created initial repository structure, Haversine geospatial math, transport economics engine, risk analysis, and single-commodity Onion recommendation engine.

### Task 1: Genuine Multi-Commodity Data Acquisition & Quarantine
- Acquired genuine historical datasets for Potato Agra (2,491 sessions), Tomato Kolar (4,770 sessions), Wheat Khanna (1,176 sessions), Wheat Indore (2,153 sessions), and Rice Burdwan (2,346 sessions). Quarantined old proxy files.

### Tasks 2–5: Genuine ML Model Training & Feature Engineering
- **Task 2 (Potato Agra):** Engineered 61 V3 features; trained XGBoost change model achieving MAE Rs.42.15/qtl (69.7 Reliability Score, `PRODUCTION_READY`).
- **Task 3 (Tomato Kolar):** Engineered 61 V3 features; trained XGBoost change model achieving MAE Rs.215.30/qtl (65.0 Reliability Score, `PRODUCTION_READY`).
- **Task 4 (Wheat Khanna & Indore):** Trained XGBoost models for Wheat Khanna (19.4 score, `DISABLED`) and Wheat Indore (38.6 score, `USABLE_WITH_WARNING`).
- **Task 5 (Rice Burdwan):** Trained XGBoost model for Rice Burdwan (7.0 score, `DISABLED`).

### Task 6: Multi-Commodity Audit & Master Benchmarking
- Built `src/benchmark/model_quality.py` and `src/tools/benchmark_model_quality.py`.
- Formulated the **0–100 Model Reliability Score**:
  $$\text{Reliability Score} = \max\left(0, 100 \times \left(1 - \frac{\text{Model MAE}}{\text{Historical Mean Price}}\right) - (2 \times \text{MAPE}) - \text{Spike Penalty}\right)$$
- Generated 4 master benchmark artifacts (`model_quality_benchmark.csv`, `model_quality_ranking.csv`, `commodity_quality_summary.csv`, `model_quality_benchmark.json`) and report `docs/TASK_6_MULTI_COMMODITY_MODEL_QUALITY_REPORT.md`.

### Task 7: Production-Grade Dynamic Inference & Model Quality Gating
- Built `src/models/model_quality_gate.py`.
- Enforced dynamic runtime gating reading `model_registry.json`. Blocked `DISABLED` and `RESEARCH_ONLY` models from farmer recommendations.
- Added 17 unit tests (`tests/test_model_quality_gate.py`).

### Task 8: Real-Time Data Freshness & Inference Reliability Layer
- Built `src/data/data_reliability.py`.
- Enforced freshness tags (`LIVE_FRESH`, `CACHE_FRESH`, `CACHE_STALE`), numeric price sanity, non-negativity, and minimum warm-up session count (`MIN_REQUIRED_HISTORY_SESSIONS = 31`).
- Added 22 unit tests (`tests/test_data_reliability.py`).

### Task 9: Production Inference Contract & Integration Readiness
- Built `src/contracts/inference_contract.py` (`CONTRACT_VERSION = "1.0.0"`) and documentation `docs/AI_INFERENCE_CONTRACT.md`.
- Exposed canonical dataclasses (`CanonicalRecommendationResponse`, `CanonicalInferenceItem`, `ContractMetadata`) with deterministic `to_json()` output and safety gate invariants.
- Added 20 unit tests (`tests/test_inference_contract.py`).

### Task 10: Final Production Validation & Backend Handoff
- Performed complete repository AI/ML audit, security audit, latency benchmarking, and data provenance verification.
- Created `docs/FINAL_AI_ML_PRODUCTION_READINESS_REPORT.md` and `docs/AI_ML_BACKEND_HANDOFF.md`.
- Verified **101/101 passing unit tests** (0 failures, 0 skipped).
- Classified final system status as **`PRODUCTION_READY_WITH_WARNINGS`**.

---

## 6. Safety & Quality Gating Architecture

The AI/ML engine operates **two independent, non-bypassable safety gates**:

```
Input Data  ──>  [Task 8 Data Reliability Gate]  ──>  [Task 7 Model Quality Gate]  ──>  XGBoost Inference
```

### Gate 1: Task 8 Data Reliability Gate
- **Purpose:** "Can we trust the input data enough to run inference?"
- **Rules Enforced:**
  - `modal_price > 0` (Rejects zero, negative, NaN, Inf values).
  - Valid datetime formatting without duplicate timestamp sessions.
  - Observed sessions count $\ge 31$ (for 30-day V3 lag/rolling feature warm-up).
  - Data recency: Cache age $> 7$ days tagged `CACHE_STALE` with mandatory warning.

### Gate 2: Task 7 Model Quality Gate
- **Purpose:** "Can we trust this trained model enough to show its forecast to a farmer?"
- **Rules Enforced:**
  - `PRODUCTION_READY` ($\text{Score} \ge 60$) $\rightarrow$ **Allowed**.
  - `USABLE_WITH_WARNING` ($35 \le \text{Score} < 60$) $\rightarrow$ **Allowed with Warning Badge**.
  - `RESEARCH_ONLY` / `DISABLED` / `MISSING` ($\text{Score} < 35$) $\rightarrow$ **Strictly BLOCKED** for farmer-facing recommendations (raises `PermissionError` or skips mandi).

---

## 7. Economic & Confidence Formulas

### 1. Transport Cost Formula
$$\text{Transport Cost (₹)} = \text{Distance (km)} \times \text{Tariff Rate (₹/quintal/km)} \times \text{Quantity (quintals)}$$

### 2. Market Fee Formula
$$\text{Market Fee (₹)} = \text{Fee Rate (₹/quintal)} \times \text{Quantity (quintals)}$$

### 3. Expected Net Return (Primary Ranking Metric)
$$\text{Gross Revenue (₹)} = \text{Predicted Modal Price (₹/quintal)} \times \text{Quantity (quintals)}$$
$$\text{Expected Net Return (₹)} = \text{Gross Revenue} - \text{Transport Cost} - \text{Market Fee}$$

### 4. Transparent Confidence Score Formula (0–100)
$$\text{Confidence Score} = \max\left(0, \min\left(100, 100 \times \left(1 - \frac{\text{Model MAE}}{\text{Current Price}}\right) - (\text{Volatility Ratio} \times 40) - \text{Spike Penalty} - \text{Recency Penalty}\right)\right)$$

---

## 8. Canonical API Integration Contract

The public contract (`src/contracts/inference_contract.py`) exposes a versioned (`1.0.0`) JSON response structure:

```json
{
  "contract_metadata": {
    "schema_version": "1.0.0",
    "generated_at": "2026-09-02T16:30:00+00:00",
    "system_id": "SIH26132_AI_ENGINE"
  },
  "commodity": "Potato",
  "farmer_latitude": 27.1767,
  "farmer_longitude": 78.0081,
  "quantity_quintals": 10.0,
  "recommended_mandi": "Agra",
  "total_mandis_evaluated": 1,
  "overall_data_source": "CACHE",
  "recommendations": [
    {
      "rank": 1,
      "mandi": "Agra",
      "state": "Uttar Pradesh",
      "district": "Agra",
      "distance_km": 12.4,
      "current_price": 1450.0,
      "predicted_price": 1495.0,
      "expected_change": 45.0,
      "expected_change_pct": 3.1,
      "expected_direction": "UP",
      "horizon_days": 1,
      "transport_cost": 372.0,
      "market_fee": 200.0,
      "gross_revenue": 14950.0,
      "total_cost": 572.0,
      "net_return": 14378.0,
      "net_price_per_quintal": 1437.8,
      "model_usage_status": "PRODUCTION_READY",
      "model_reliability_score": 69.7,
      "model_quality_class": "STRONG",
      "data_source": "CACHE",
      "data_freshness_status": "CACHE_STALE",
      "data_age_days": 303,
      "historical_session_count": 2491,
      "data_reliability_status": "CACHE_STALE",
      "data_reliability_warning": "Market data for Potato Agra is from cached data (303 days old, threshold: 7 days).",
      "risk_level": "LOW",
      "confidence_score": 85.0,
      "market_condition": "NORMAL",
      "recommendation_label": "RECOMMENDED",
      "reason": "Recommended as top mandi providing the highest expected net return of Rs.14,378.00 after deducting Rs.372.00 transport cost for 12.4 km.",
      "warning": "Market data for Potato Agra is from cached data (303 days old, threshold: 7 days).",
      "lower_bound_80": 1410.0,
      "upper_bound_80": 1580.0
    }
  ]
}
```

---

## 9. Test Suite & Verification Commands

The test suite covers **101 unit and integration tests** across 18 test files:

```bash
# Run full test suite
python -m unittest discover -s tests -p "test_*.py"
```

### Output Verification:
```
Ran 101 tests in 318.292s
OK — 0 failures, 0 skipped
```

### CLI Verification Scripts:
```bash
# Multi-Commodity CLI check
python -m src.tools.validate_task8_cli

# Performance & Latency Benchmark
python -m src.tools.measure_performance

# Model Quality Audit & Benchmark Generator
python -m src.tools.benchmark_model_quality
```

---

## 10. Developer & Teammate Integration Guide

### How Backend Developers Consume the AI Layer:

```python
from src.recommendation.mandi_recommender import recommend_canonical

# 1. Execute recommendation
response = recommend_canonical(
    farmer_latitude=27.1767,
    farmer_longitude=78.0081,
    quantity_quintals=10.0,
    commodity="Potato",
    farmer_facing=True
)

# 2. Serialize to canonical JSON string
json_output = response.to_json(indent=2)
```

### Key Integration Rules for Backend Teammates:
1. **Handling `"recommended_mandi": "NONE"`:** Indicates all local mandis were blocked by safety gates (e.g. models disabled or data invalid). Render a notice: *"Market forecasts are currently unavailable in your area."*
2. **Warning Badges:** Display `item.warning` and `item.data_reliability_warning` in the UI as warning badges.
3. **Primary Metric:** Mandis are sorted by `net_return` (Expected Net Return), not highest price.

---

## 11. Government Market Data Explorer

### Overview & Architectural Separation
The **Government Mandi Market Data Explorer** (`src/data/market_data_service.py`) provides independent current market data, historical price chart data, and market options discovery for **any commodity and mandi** available from official government sources (`data.gov.in` / AGMARKNET).

> [!IMPORTANT]
> **Strict Architectural Separation:**
> - Market Data functions do **NOT** invoke XGBoost models, `ModelPredictor`, `ModelQualityGate`, `MandiRecommender`, `RiskEngine`, or `EconomicsEngine`.
> - Market Data functions do **NOT** require an ML prediction model to exist. Farmers can view government market prices for any crop.
> - ML Prediction functionality remains completely unchanged.

### Key Python API Functions:

#### 1. Current Market Data Query
```python
from src.data.market_data_service import get_current_market_data

response = get_current_market_data(commodity="Potato", market="Agra")
print(response.to_json(indent=2))
```

#### 2. Historical Market Data Query (Frontend Price Chart)
```python
from src.data.market_data_service import get_historical_market_data

response = get_historical_market_data(
    commodity="Potato",
    market="Agra",
    start_date="2024-01-01",
    end_date="2024-06-30"
)
print(response.to_json(indent=2))
```

#### 3. Available Market Options Discovery
```python
from src.data.market_data_service import get_available_market_options

options = get_available_market_options()
print(options.to_json(indent=2))
```

### JSON Response Contracts

#### Current Market Data JSON Response Example:
```json
{
  "status": "SUCCESS",
  "commodity": "Potato",
  "market": "Agra",
  "location": {
    "state": "Uttar Pradesh",
    "district": "Agra"
  },
  "data": {
    "commodity": "Potato",
    "market": "Agra",
    "state": "Uttar Pradesh",
    "district": "Agra",
    "date": "2026-09-03",
    "min_price": 1100.0,
    "max_price": 1300.0,
    "modal_price": 1200.0,
    "arrival": 150.0,
    "unit": "Rs/quintal"
  },
  "metadata": {
    "source": "CACHE",
    "freshness_status": "CACHE_STALE",
    "data_age_days": 304,
    "record_count": 1,
    "warning": "Current market data for Potato Agra is from cached data (304 days old)."
  }
}
```

#### Historical Market Data JSON Response Example (Frontend Price Chart):
```json
{
  "status": "SUCCESS",
  "commodity": "Potato",
  "market": "Agra",
  "location": {
    "state": "Uttar Pradesh",
    "district": "Agra"
  },
  "date_range": {
    "from": "2024-01-01",
    "to": "2024-01-02"
  },
  "records": [
    {
      "date": "2024-01-01",
      "min_price": 1000.0,
      "max_price": 1200.0,
      "modal_price": 1100.0,
      "arrival": 50.0
    },
    {
      "date": "2024-01-02",
      "min_price": 1050.0,
      "max_price": 1250.0,
      "modal_price": 1150.0,
      "arrival": 60.0
    }
  ],
  "metadata": {
    "source": "CACHE",
    "record_count": 2
  }
}
```

