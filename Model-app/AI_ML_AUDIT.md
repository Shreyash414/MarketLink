# SIH26132 AI/ML & Data Pipeline Audit

This document provides a comprehensive audit of all data, machine learning, recommendation, and AI components in the SIH26132 repository.

---

## 1. Component Classification Matrix

| Component / File | Primary Purpose | Classification | Reason / Notes |
|---|---|---|---|
| `src/config/commodity_registry.py` | Central commodity metadata & registry | **VALIDATED** | Fully generic dataclass & dynamic registry supporting any commodity with runtime fallback. |
| `src/config/model_registry.py` | JSON model catalogue persistence | **VALIDATED** | Dynamic storage and query by `(commodity, market)`. Tested and operational. |
| `src/config/config.py` | System-wide paths, API settings, economic defaults | **VALIDATED** | Dynamic path resolvers (`get_current_data_file`, `get_model_dir`) maintaining backward compatibility. |
| `src/data/ingestion/current_data_fetcher.py` | Live AGMARKNET fetcher with cache fallback | **VALIDATED** | Accepts dynamic `commodity` and `market` parameters; circuit breaker and clean fallback implemented. |
| `src/data/preprocessing/historical_merger.py` | Merge recent history with current observation | **VALIDATED** | Dynamic `commodity` lookup and chronological deduplication; lookback window warm-up logic. |
| `src/features/inference_feature_generator.py` | V3 lag, rolling mean, momentum, trend features | **VALIDATED** | Fully commodity-agnostic time-series feature engineering without future leakage. |
| `src/models/model_predictor.py` | Pre-trained XGBoost V3 inference engine | **VALIDATED** | Dynamic model resolution by crop and mandi with caching and registry support. |
| `src/risk/risk_engine.py` | Volatility, spike detection, transparent confidence | **VALIDATED** | Dynamic historical MAE lookup per crop/market; 0–100 score + risk level categorization. |
| `src/economics/economics_engine.py` | Transport tariff, market fee, gross & net return | **VALIDATED** | Strictly mathematical economics engine with configurable tariffs. |
| `src/utils/geo_utils.py` | Haversine GPS distance calculator | **VALIDATED** | Pure mathematical geospatial module. |
| `src/recommendation/mandi_recommender.py` | End-to-end recommendation orchestrator | **VALIDATED** | Dynamic crop, location, quantity, distance filtering, and ranking by Expected Net Return. |
| `src/recommendation/schemas.py` | Dataclass schemas for recommendation output | **VALIDATED** | Strict contracts (`RecommendationResult`, `MandiRecommendationItem`) ready for LLM consumption. |
| `src/tools/commodity_discovery.py` | Discovers reporting mandis & data quality score | **VALIDATED** | Computes 0–100 quality scores based on volume, validity, density, and stability. |
| `src/tools/train_commodity_model.py` | Parameterized XGBoost V3 trainer & feature selector | **VALIDATED** | CLI & programmatic trainer with temporal splits and model registry auto-registration. |
| `src/tools/batch_recommend.py` | Batch CSV farmer query processor | **VALIDATED** | High-throughput batch processor with formatted CLI tables and CSV outputs. |
| `src/recommend_mandi.py` | Farmer CLI entry point | **VALIDATED** | Production wrapper for single farmer recommendation. |
| `src/create_model_datasets.py` | Historical Onion dataset cleaner | **ONION-SPECIFIC** | Hardcoded for Onion Bareilly/Bargarh/Nagpur. Retained for provenance. |
| `src/download_selected_markets.py` | Historical Onion downloader | **ONION-SPECIFIC** | Historical download script for Onion. Retained for provenance. |
| `src/find_top_onion_markets.py` | Historical Onion market discovery | **ONION-SPECIFIC** | Onion research script. Retained for provenance. |
| `src/eda_market_analysis.py` | Onion exploratory data analysis | **ONION-SPECIFIC** | Generates plots for Onion. Retained for provenance. |
| `src/tune_xgboost.py` | Historical hyperparameter tuning for Onion | **ONION-SPECIFIC** | Tuned parameters for Onion V3. Retained for provenance. |
| `src/detect_price_spikes.py` | Onion spike threshold analysis | **ONION-SPECIFIC** | Onion research script. Retained for provenance. |
| `src/benchmark/model_quality.py` | Core benchmarking, scoring & gating module | **VALIDATED** | Commodity-agnostic module for baseline comparisons, error percentiles, spike robustness, 0-100 reliability score, and usage gating. Bug fix applied: change-model prediction now correctly computed as `modal_price + y_pred_change`. |
| `src/tools/benchmark_model_quality.py` | CLI audit & benchmark generator | **VALIDATED** | Command-line tool that audits all genuine models, updates `model_registry.json` gating, and writes CSV/JSON/MD benchmark reports. |
| `src/models/model_quality_gate.py` | Centralized production-safety gating layer | **VALIDATED** | Provides `get_model_quality_metadata`, `can_use_model`, `evaluate_model_gating`. Reads `model_registry.json` at runtime and enforces farmer-facing gating rules deterministically. |
| `src/data/data_reliability.py` | Centralized data freshness & inference reliability layer | **VALIDATED** | Provides `DataReliabilityResult`, `evaluate_data_freshness`, `validate_price_data`, `evaluate_historical_sufficiency`, `evaluate_data_reliability`. Prevents stale, malformed, or insufficient input data from reaching models. |
| `src/contracts/inference_contract.py` | Production inference contract & integration readiness | **VALIDATED** | Provides canonical dataclasses (`ContractMetadata`, `CanonicalInferenceItem`, `CanonicalRecommendationResponse`), validation logic, and helpers for backend integration. |
| `src/data/market_data_service.py` | Government Mandi Market Data Explorer service | **VALIDATED** | Decoupled market data service (`get_current_market_data`, `get_historical_market_data`, `get_available_market_options`) providing raw data queries without ML dependency. |

---

## 2. Hardcoding Analysis

### Generic Pipeline Modules (Core System)
- **`mandi_recommender.py`**: Clean. Uses `get_commodity_config(commodity)` and dynamic market metadata.
- **`model_predictor.py`**: Clean. Resolves directory via `get_model_dir(commodity)` and checks `model_registry.json`.
- **`risk_engine.py`**: Clean. Looks up historical MAE from registry/config.
- **`historical_merger.py`**: Clean. Routes files based on `{commodity}_{market}` pattern.
- **`current_data_fetcher.py`**: Clean. Filters API and cache by `target_commodity`.
- **`train_commodity_model.py`**: Clean. Fully parameterized CLI `--commodity` and `--market`.
- **`commodity_discovery.py`**: Clean. Parameterized `--commodity`.
- **`model_quality.py`**: Clean. Dynamically benchmarks genuine trained models from registry and split paths.
- **`data_reliability.py`**: Clean. Parameterized freshness age thresholds, session counts, and validation checks.
- **`inference_contract.py`**: Clean. Dynamic canonical response builder with strict validation rules.
- **`market_data_service.py`**: Clean. Case-insensitive commodity/market matching and clean JSON serialization.

### Fixed Items in Recent Sessions
- `src/recommend_mandi.py`: Removed hardcoded `print("Commodity : Onion")` and added parameter documentation.

---

## 3. Test Suite Baseline
- **118 Automated Tests**: Comprehensive unit & integration test coverage across geospatial, economics, risk & confidence, ingestion, feature generation, predictor, multi-commodity inference, historical quality, model benchmarking/gating, model quality gate enforcement, data freshness & reliability, production inference contracts, and market data explorer service.
- **Current Status**: **118/118 Passing (100%)**.
- **New in Task 7**: `tests/test_model_quality_gate.py` (17 tests) — validates gating rules for all usage statuses, end-to-end recommender filtering, missing model handling, and structured warning propagation.
- **New in Task 8**: `tests/test_data_reliability.py` (22 tests) — validates freshness evaluation, price validation, historical warm-up sufficiency, CACHE vs LIVE semantics, stale cache warning policy, and end-to-end reliability integration.
- **New in Task 9**: `tests/test_inference_contract.py` (20 tests) — validates canonical contract building, validation rules, status enums, JSON serialization, safety gate invariants, and backward compatibility.
- **New in Task 11**: `tests/test_market_data_service.py` (17 tests) — validates current market data retrieval, historical chart points, options discovery, date range filtering, empty response safety, `LIVE`/`CACHE` status tags, stale cache warnings, JSON serialization, and zero ML invocation.
- **Task 10 Final Audit**: Complete repository audit verified, real-data provenance confirmed, zero security leaks found, latency measured, and handoff documentation created (`docs/AI_ML_BACKEND_HANDOFF.md`, `docs/FINAL_AI_ML_PRODUCTION_READINESS_REPORT.md`). Final Classification: `PRODUCTION_READY_WITH_WARNINGS`.



