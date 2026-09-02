# SIH26132 — Production AI Inference Contract & Integration Specification

**Version:** `1.0.0`  
**Status:** VALIDATED & PRODUCTION-READY  
**Target Audience:** Backend Developers (Spring Boot / REST API / Integration Layer)

---

## 1. Overview & Architectural Boundary

The **SIH26132 AI Inference Contract** establishes a strict, stable, versioned JSON interface between the Python AI/ML core and external application backends.

### Key Boundary Principles:
1. **Decoupled Intelligence:** The backend interacts purely with canonical JSON payloads. Internal ML details (XGBoost tree structures, feature selection matrices, raw CSV file paths) are completely hidden.
2. **Deterministic Safety Gating:** Two independent safety gates are enforced prior to contract generation:
   - **Task 8 Data Reliability Gate:** Validates price data numeric integrity, non-negativity, non-NaN/Inf, chronological ordering, and historical warm-up sufficiency (>=31 observed sessions).
   - **Task 7 Model Quality Gate:** Enforces model approval status based on measured historical performance (`PRODUCTION_READY`, `USABLE_WITH_WARNING`, `RESEARCH_ONLY`, `DISABLED`, `MISSING`).
3. **Safety Invariants:** 
   - Neither gate can be bypassed by the contract.
   - Any market item with `DISABLED`, `RESEARCH_ONLY`, `MISSING`, or `BLOCKED` status is **NEVER** assigned `recommendation_label: "RECOMMENDED"` for farmer-facing recommendations.
4. **Separate Scores:** Model confidence/reliability (`model_reliability_score`) and Data freshness (`data_freshness_status`, `data_age_days`) are presented as distinct, transparent fields.

---

## 2. Request Concept

The AI engine accepts the following input parameters:

| Field | Type | Description | Example |
|---|---|---|---|
| `commodity` | `string` | Target crop name | `"Potato"` |
| `farmer_latitude` | `float` | Farmer GPS Latitude | `27.1767` |
| `farmer_longitude` | `float` | Farmer GPS Longitude | `78.0081` |
| `quantity_quintals` | `float` | Harvested produce quantity in quintals | `10.0` |
| `max_distance_km` | `float?` | Optional maximum search radius in km | `100.0` |
| `farmer_facing` | `boolean` | `true` for farmer UI; `false` for dev/research mode | `true` |

---

## 3. Response Schema Specification

### 3.1 `ContractMetadata`

| Field | Type | Description |
|---|---|---|
| `schema_version` | `string` | Version of the contract specification (`"1.0.0"`) |
| `generated_at` | `string (ISO 8601)` | Timestamp when the response was generated |
| `system_id` | `string` | Identifier of the generating engine (`"SIH26132_AI_ENGINE"`) |

### 3.2 `CanonicalRecommendationResponse` (Top-Level Container)

| Field | Type | Description |
|---|---|---|
| `contract_metadata` | `object` | Header metadata (`ContractMetadata`) |
| `commodity` | `string` | Requested commodity |
| `farmer_latitude` | `float` | Input farmer latitude |
| `farmer_longitude` | `float` | Input farmer longitude |
| `quantity_quintals` | `float` | Input harvest quantity in quintals |
| `recommended_mandi` | `string` | Name of top-ranked mandi (or `"NONE"` if all blocked) |
| `total_mandis_evaluated` | `integer` | Number of mandis passing safety gates |
| `overall_data_source` | `string` | Data acquisition channel (`"LIVE"` or `"CACHE"`) |
| `recommendations` | `array[object]` | Ordered list of `CanonicalInferenceItem` objects (highest net return first) |

### 3.3 `CanonicalInferenceItem` (Per-Mandi Intelligence Payload)

| Field | Type | Description | Allowed Values |
|---|---|---|---|
| `rank` | `integer` | Economic rank (1 = Top choice) | `1, 2, 3...` |
| `mandi` | `string` | Market name | e.g. `"Agra"` |
| `state` | `string` | State name | e.g. `"Uttar Pradesh"` |
| `district` | `string` | District name | e.g. `"Agra"` |
| `distance_km` | `float` | Haversine distance from farmer | e.g. `24.5` |
| `current_price` | `float` | Latest observed modal price (₹/quintal) | `> 0` |
| `predicted_price` | `float` | Forecasted next session modal price (₹/quintal) | `> 0` |
| `expected_change` | `float` | Forecasted price difference (₹/quintal) | e.g. `+45.0` |
| `expected_change_pct` | `float` | Forecasted percentage price change | e.g. `+3.15%` |
| `expected_direction` | `string` | Forecasted direction | `"UP"`, `"DOWN"`, `"STABLE"` |
| `horizon_days` | `integer` | Forecasting horizon in sessions | `1` |
| `transport_cost` | `float` | Total logistics cost for harvest (₹) | `> 0` |
| `market_fee` | `float` | Total mandi fee for harvest (₹) | `> 0` |
| `gross_revenue` | `float` | `predicted_price * quantity` (₹) | `> 0` |
| `total_cost` | `float` | `transport_cost + market_fee` (₹) | `> 0` |
| `net_return` | `float` | **Primary Ranking Metric:** `gross_revenue - total_cost` (₹) | float |
| `net_price_per_quintal` | `float` | Net effective price realized per quintal (₹) | float |
| `model_usage_status` | `string` | Task 7 Model Quality Gate status | `"PRODUCTION_READY"`, `"USABLE_WITH_WARNING"`, `"RESEARCH_ONLY"`, `"DISABLED"`, `"MISSING"` |
| `model_reliability_score` | `float` | Benchmark reliability score out of 100 | `0.0` to `100.0` |
| `model_quality_class` | `string` | Model accuracy classification | `"STRONG"`, `"ACCEPTABLE"`, `"WEAK"`, `"REJECT"` |
| `data_source` | `string` | Data source origin | `"LIVE"`, `"CACHE"` |
| `data_freshness_status` | `string` | Data recency status | `"LIVE_FRESH"`, `"CACHE_FRESH"`, `"CACHE_STALE"` |
| `data_age_days` | `integer` | Age of latest observation in days | `>= 0` |
| `historical_session_count` | `integer` | Number of observed warm-up sessions | `>= 31` |
| `data_reliability_status` | `string` | Task 8 Data Reliability Gate status | `"READY"`, `"BLOCKED"`, `"CACHE_STALE"`, `"INSUFFICIENT_HISTORY"`, `"INVALID_DATA"` |
| `data_reliability_warning` | `string` | Structured data freshness warning message | string |
| `risk_level` | `string` | Price volatility risk level | `"LOW"`, `"MEDIUM"`, `"HIGH"` |
| `confidence_score` | `float` | Overall forecast confidence out of 100 | `0.0` to `100.0` |
| `market_condition` | `string` | Volatility state | `"NORMAL"`, `"ELEVATED_VOLATILITY"`, `"UNUSUAL_SPIKE"` |
| `recommendation_label` | `string` | Label | `"RECOMMENDED"`, `"ALTERNATIVE"` |
| `reason` | `string` | Structured economic recommendation explanation | string |
| `warning` | `string` | Consolidated warning string (model + data + risk) | string |
| `lower_bound_80` | `float` | 80% empirical prediction interval lower bound | float |
| `upper_bound_80` | `float` | 80% empirical prediction interval upper bound | float |

---

## 4. JSON Response Examples

### 4.1 Example 1: Successful Production-Ready Recommendation (`Potato / Agra`)
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

### 4.2 Example 2: Recommendation with Warning (`Wheat / Indore`)
```json
{
  "contract_metadata": {
    "schema_version": "1.0.0",
    "generated_at": "2026-09-02T16:30:00+00:00",
    "system_id": "SIH26132_AI_ENGINE"
  },
  "commodity": "Wheat",
  "farmer_latitude": 22.7196,
  "farmer_longitude": 75.8577,
  "quantity_quintals": 10.0,
  "recommended_mandi": "Indore",
  "total_mandis_evaluated": 1,
  "overall_data_source": "CACHE",
  "recommendations": [
    {
      "rank": 1,
      "mandi": "Indore",
      "state": "Madhya Pradesh",
      "district": "Indore",
      "distance_km": 18.2,
      "current_price": 2597.0,
      "predicted_price": 2456.9,
      "expected_change": -140.1,
      "expected_change_pct": -5.39,
      "expected_direction": "DOWN",
      "horizon_days": 1,
      "transport_cost": 546.0,
      "market_fee": 200.0,
      "gross_revenue": 24569.0,
      "total_cost": 746.0,
      "net_return": 23823.0,
      "net_price_per_quintal": 2382.3,
      "model_usage_status": "USABLE_WITH_WARNING",
      "model_reliability_score": 38.6,
      "model_quality_class": "ACCEPTABLE",
      "data_source": "CACHE",
      "data_freshness_status": "CACHE_STALE",
      "data_age_days": 491,
      "historical_session_count": 2153,
      "data_reliability_status": "CACHE_STALE",
      "data_reliability_warning": "Market data for Wheat Indore is from cached data (491 days old, threshold: 7 days).",
      "risk_level": "MEDIUM",
      "confidence_score": 63.6,
      "market_condition": "ELEVATED_VOLATILITY",
      "recommendation_label": "RECOMMENDED",
      "reason": "Recommended as top mandi providing expected net return of Rs.23,823.00 at a distance of 18.2 km.",
      "warning": "Model for Wheat / Indore has moderate historical error; predictions carry higher uncertainty. Market data for Wheat Indore is from cached data (491 days old, threshold: 7 days). Forecast uncertainty is moderate due to elevated short-term price volatility.",
      "lower_bound_80": 2295.7,
      "upper_bound_80": 2618.1
    }
  ]
}
```

### 4.3 Example 3: Blocked Model Response (`Rice / Burdwan`)
```json
{
  "contract_metadata": {
    "schema_version": "1.0.0",
    "generated_at": "2026-09-02T16:30:00+00:00",
    "system_id": "SIH26132_AI_ENGINE"
  },
  "commodity": "Rice",
  "farmer_latitude": 23.2324,
  "farmer_longitude": 87.8615,
  "quantity_quintals": 10.0,
  "recommended_mandi": "NONE",
  "total_mandis_evaluated": 0,
  "overall_data_source": "CACHE",
  "recommendations": []
}
```

---

## 5. Contract Validation & Invariants

Validation is programmatically enforced via `validate_inference_contract()`:

1. **Numerical Integrity:**
   - `confidence_score` MUST be within `[0.0, 100.0]`.
   - `model_reliability_score` MUST be within `[0.0, 100.0]`.
   - `current_price` and `predicted_price` MUST be non-negative.
2. **Safety Gate Invariants:**
   - Items with `model_usage_status` equal to `"DISABLED"`, `"RESEARCH_ONLY"`, or `"MISSING"` will trigger a validation error if assigned `recommendation_label: "RECOMMENDED"`.
   - Items with `data_reliability_status` equal to `"BLOCKED"`, `"INVALID_DATA"`, or `"INSUFFICIENT_HISTORY"` will trigger a validation error if assigned `recommendation_label: "RECOMMENDED"`.

---

## 6. Integration Instructions for Backend Teammate

1. **Invoke Recommendation:**
   Call `recommend_canonical(farmer_latitude, farmer_longitude, quantity_quintals, commodity)` from Python, or serialize `RecommendationResult.to_canonical_contract().to_json()`.
2. **Handle `"NONE"` Top Mandi:**
   If `recommended_mandi == "NONE"` and `recommendations` is empty, all local candidate mandis failed safety gates (e.g. models disabled or data insufficient). Display a friendly UI notice indicating market forecast is currently unavailable.
3. **Display Structured Warnings:**
   Always inspect `item.warning` and `item.data_reliability_warning`. If present, render them in UI notification badges.
