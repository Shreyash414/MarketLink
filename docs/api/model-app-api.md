# Model-App Internal API Reference

## 1. Overview & Service Boundary

The FastAPI Model-app is an **internal microservice** deployed on the private application network. It communicates strictly with the Core Backend and is never exposed directly to mobile devices or third-party clients.

- **Default Address**: `http://localhost:8000` (Private)
- **ASGI Framework**: FastAPI / Uvicorn
- **Serialization Standard**: Pydantic v2 schemas (`snake_case` JSON fields)
- **Tracing**: Preserves and logs `X-Correlation-ID` header

---

## 2. Endpoints Reference

### 2.1 Mandi Market Data (`GET /api/v1/market-data`)
- **Summary**: Retrieve daily AGMARKNET mandi modal prices and arrivals.
- **Query Parameters**:
  - `commodity`: string (default `"Onion"`)
  - `markets`: list of strings (optional filter)
  - `state`: string (optional filter)
  - `limit`: integer (default 50, range 1–500)
- **Response (`200 OK`)**:
```json
{
  "commodity": "Onion",
  "data_source": "LIVE",
  "is_live": true,
  "record_count": 1,
  "records": [
    {
      "state": "Maharashtra",
      "district": "Nagpur",
      "market": "Nagpur",
      "commodity": "Onion",
      "modal_price": 1950.0,
      "min_price": 1800.0,
      "max_price": 2100.0,
      "date": "2026-09-03"
    }
  ]
}
```

---

### 2.2 Next-Day Price Prediction (`POST /api/v1/predict`)
- **Summary**: Forecasts next-day modal price using trained XGBoost regressors.
- **Request Body**:
```json
{
  "market": "Bareilly",
  "commodity": "Onion",
  "current_price": 1850.0,
  "farmer_facing": true
}
```
- **Response (`200 OK`)**:
```json
{
  "market": "Bareilly",
  "commodity": "Onion",
  "current_price": 1850.0,
  "predicted_price": 1920.0,
  "expected_change": 70.0,
  "expected_change_pct": 3.78,
  "expected_direction": "UP",
  "usage_status": "PRODUCTION_READY",
  "reliability_score": 92.0,
  "quality_class": "STRONG",
  "data_source": "DIRECT"
}
```

---

### 2.3 Synchronous Mandi Recommendation (`POST /api/v1/recommend`)
- **Summary**: Evaluates regional mandis by gross revenue, haulage costs, and mandi fees.
- **Request Body**:
```json
{
  "commodity": "Onion",
  "farmer_latitude": 28.6139,
  "farmer_longitude": 77.2090,
  "quantity_quintals": 10.0,
  "max_distance_km": 200.0,
  "top_n": 5
}
```
- **Response (`200 OK`)**:
```json
{
  "commodity": "Onion",
  "farmer_latitude": 28.6139,
  "farmer_longitude": 77.2090,
  "quantity_quintals": 10.0,
  "recommended_mandi": "Bareilly",
  "total_mandis_evaluated": 1,
  "overall_data_source": "CACHE",
  "recommendations": [
    {
      "rank": 1,
      "mandi": "Bareilly",
      "state": "Uttar Pradesh",
      "district": "Bareilly",
      "distance_km": 15.2,
      "current_price": 1850.0,
      "predicted_price": 1920.0,
      "expected_change": 70.0,
      "expected_change_pct": 3.78,
      "expected_direction": "UP",
      "transport_cost": 45.0,
      "market_fee": 18.0,
      "gross_revenue": 19200.0,
      "total_cost": 630.0,
      "net_return": 18570.0,
      "net_price_per_quintal": 1857.0,
      "risk_level": "LOW",
      "confidence_score": 85.0,
      "recommendation_label": "RECOMMENDED",
      "model_usage_status": "PRODUCTION_READY",
      "model_reliability_score": 90.0,
      "model_quality_class": "STRONG",
      "data_source": "CACHE"
    }
  ]
}
```

---

### 2.4 Asynchronous Recommendation Intake (`POST /api/v1/recommend/async`)
- **Status Code**: `202 Accepted`
- **Response Schema**:
```json
{
  "job_id": "8c39e240-5a21-4f12-8e9a-0123456789bc",
  "status": "QUEUED",
  "operation": "RECOMMEND_MANDI",
  "created_at": "2026-09-03T12:00:00Z",
  "message": "Job successfully enqueued",
  "poll_url": "/api/v1/jobs/8c39e240-5a21-4f12-8e9a-0123456789bc"
}
```

---

### 2.5 Job Status Polling (`GET /api/v1/jobs/{job_id}`)
- **Response (`200 OK`)**:
```json
{
  "job_id": "8c39e240-5a21-4f12-8e9a-0123456789bc",
  "operation": "RECOMMEND_MANDI",
  "status": "COMPLETED",
  "created_at": "2026-09-03T12:00:00Z",
  "updated_at": "2026-09-03T12:00:02Z",
  "completed_at": "2026-09-03T12:00:02Z",
  "result": {
    "recommended_mandi": "Bareilly",
    "net_return": 18570.0
  }
}
```

---

### 2.6 Ollama General Query (`POST /api/v1/query`)
- **Request Schema**:
```json
{
  "query": "How to cure and store harvested onions?",
  "language": "en"
}
```
- **Response Schema (`200 OK`)**:
```json
{
  "query": "How to cure and store harvested onions?",
  "intent": "GENERAL_ADVISORY",
  "entities": {
    "commodity": "Onion"
  },
  "response": "Cure harvested onions in a shaded, well-ventilated dry area for 2-3 weeks until necks are completely dry before bulk crating.",
  "language": "en",
  "confidence": 0.95,
  "source": "OLLAMA_LLM",
  "model": "llama3",
  "timestamp": "2026-09-03T12:00:00Z"
}
```

---

### 2.7 System Probes (`/health`, `/ready`)
- `GET /health` (`200 OK`):
```json
{"status": "HEALTHY", "service": "marketlink-ai", "version": "1.0.0"}
```
- `GET /ready` (`200 OK` or `503 Service Unavailable`):
```json
{
  "ready": false,
  "status": "NOT_READY",
  "dependencies": {
    "redis": {"available": false, "status": "DOWN"},
    "rabbitmq": {"available": false, "status": "DOWN"},
    "ml_predictor": {"available": true, "status": "UP"}
  }
}
```
