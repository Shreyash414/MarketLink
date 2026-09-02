# SIH26132 — AI/ML Engine Backend Handoff Guide

**Target Audience:** Backend Developers (Spring Boot / REST API / Integration Layer)  
**Contract Version:** `1.0.0`  
**Status:** PRODUCTION-READY & VALIDATED  

---

## 1. Executive Summary

This guide explains how to integrate the **SIH26132 Python AI/ML Recommendation Engine** into the application backend.

The backend teammate does **NOT** need to understand:
- XGBoost machine learning internals
- Feature engineering (lags, rolling averages, momentum)
- Dataset cleaning or historical CSV merging
- Model training or model selection

The Python AI/ML layer exposes a **single, versioned, JSON-serializable canonical contract** (`CanonicalRecommendationResponse`) that contains all necessary price predictions, market recommendations, transport economics, risk scores, data freshness warnings, and human-readable explanations.

---

## 2. Integration Boundary Architecture

```
[Farmer Mobile App / Web UI]
         │
         ▼
[Backend Service (Spring Boot / REST API)]
         │  (Constructs Python Call or REST Request)
         ▼
[Python AI/ML Engine]
   ├─> recommend_canonical(lat, lon, quantity, commodity)
   ├─> Task 8 Data Reliability Gate
   ├─> Task 7 Model Quality Gate
   ├─> XGBoost Inferences
   └─> Returns JSON String / Canonical Object
         │
         ▼
[Backend Service (Spring Boot / REST API)]
         │  (Consumes JSON payload, checks recommended_mandi)
         ▼
[Farmer Mobile App / Web UI]
```

---

## 3. Input Request Format

The backend passes the following input parameters to the AI/ML layer:

| Parameter | Type | Required | Description | Example |
|---|---|---|---|---|
| `commodity` | `string` | Yes | Target crop name | `"Potato"`, `"Tomato"`, `"Wheat"`, `"Onion"`, `"Rice"` |
| `farmer_latitude` | `float` | Yes | Farmer GPS Latitude | `27.1767` |
| `farmer_longitude` | `float` | Yes | Farmer GPS Longitude | `78.0081` |
| `quantity_quintals` | `float` | Yes | Produce quantity in quintals | `10.0` |
| `max_distance_km` | `float?` | Optional | Max search radius in km | `100.0` (Default: null/unlimited) |
| `farmer_facing` | `boolean` | Optional | Enforce safety gates for farmers | `true` (Default: true) |

### Python Invocation Example:
```python
from src.recommendation.mandi_recommender import recommend_canonical

# Generate canonical recommendation contract
canonical_response = recommend_canonical(
    farmer_latitude=27.1767,
    farmer_longitude=78.0081,
    quantity_quintals=10.0,
    commodity="Potato",
    farmer_facing=True
)

# Convert to JSON string for API transmission
json_payload = canonical_response.to_json(indent=2)
```

---

## 4. Canonical Output Contract Structure

The response object is structured as follows:

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

## 5. Essential Backend Rules & Handling Logic

### Rule 1: Handling `"recommended_mandi": "NONE"`
If all candidate mandis in a region fail Task 7 (Model Quality) or Task 8 (Data Reliability) safety gates, the response returns:
- `"recommended_mandi": "NONE"`
- `"total_mandis_evaluated": 0`
- `"recommendations": []`

**Backend Behavior:** Render a user-friendly UI message: *"Market price forecasting is currently unavailable for this crop in your area due to model quality or data freshness safety policies."* Do **NOT** attempt to parse predictions.

### Rule 2: Preserving & Displaying Structured Warnings
If `model_usage_status == "USABLE_WITH_WARNING"` or `data_freshness_status == "CACHE_STALE"`, the AI layer attaches text to `item.warning` and `item.data_reliability_warning`.

**Backend Behavior:** Pass these warning strings directly to the frontend. Render them inside warning badges (e.g. *"Predictions carry higher uncertainty due to historical model error"* or *"Data is from cached market observations"*).

### Rule 3: Economic Ranking Metric
Mandis inside `recommendations` are sorted in descending order by **`net_return`** (Expected Net Return), **NOT** highest predicted price.
- `gross_revenue = predicted_price * quantity_quintals`
- `total_cost = transport_cost + market_fee`
- `net_return = gross_revenue - total_cost`

---

## 6. Full Contract Documentation
For complete field-by-field descriptions, status enum specifications, and detailed JSON examples, refer to:
[docs/AI_INFERENCE_CONTRACT.md](file:///c:/Users/alone/OneDrive/Desktop/SIH26132/docs/AI_INFERENCE_CONTRACT.md)
