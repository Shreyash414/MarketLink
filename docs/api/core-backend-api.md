# Core Backend API Reference

## 1. Overview & Base URL

The Core Backend serves as the authenticated public API gateway for the MarketLink platform.

- **Base URL**: `http://localhost:8080` (Development)
- **API Version**: `v1`
- **Authentication**: Stateless JWT Bearer token via `Authorization: Bearer <token>`
- **Correlation ID**: Supported via `X-Correlation-ID` header (preserved or auto-generated)
- **Interactive Swagger UI**: `http://localhost:8080/swagger-ui/index.html`
- **OpenAPI 3 JSON Spec**: `http://localhost:8080/v3/api-docs`

---

## 2. AI Advisory & Query Routing Endpoints (`/api/v1/ai`)

### 2.1 Natural Language Intelligent Query
- **Path**: `POST /api/v1/ai/query`
- **Description**: Classifies farmer questions deterministically and routes dynamically to Market Data, ML Price Prediction, Mandi Recommendation, or General LLM Advisory.
- **Security**: Authenticated (`BearerAuth`)
- **Request Body**:
```json
{
  "query": "What price can I expect for onions next week?",
  "language": "en",
  "crop": "Onion",
  "market": "Bareilly",
  "location": {
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "quantity_quintals": 10.0,
  "current_price": 1850.0
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Query processed successfully",
  "data": {
    "type": "PRICE_PREDICTION",
    "confidence": 0.90,
    "answer": "Next-day forecasted price for Onion in Bareilly is ₹1920.0/quintal (Expected change: +₹70.0, UP). Model reliability: STRONG (Score: 92.0%).",
    "prediction": {
      "market": "Bareilly",
      "commodity": "Onion",
      "current_price": 1850.0,
      "predicted_price": 1920.0,
      "expected_change": 70.0,
      "expected_change_pct": 3.78,
      "expected_direction": "UP",
      "usage_status": "PRODUCTION_READY",
      "reliability_score": 92.0,
      "quality_class": "STRONG"
    },
    "timestamp": "2026-09-03T12:00:00Z"
  },
  "timestamp": "2026-09-03T12:00:00Z"
}
```

---

### 2.2 Direct Price Prediction
- **Path**: `POST /api/v1/ai/predict`
- **Description**: Forecasts next-day modal price for a commodity in a market using trained XGBoost regressors.
- **Request Body**:
```json
{
  "market": "Bareilly",
  "commodity": "Onion",
  "current_price": 1850.0,
  "farmer_facing": true
}
```
- **Response (`200 OK`)**: Standard `ModelAppPredictionResponse` in `ApiResponse` envelope.

---

### 2.3 Synchronous Mandi Recommendation
- **Path**: `POST /api/v1/ai/recommend`
- **Description**: Calculates ranked regional mandis and net returns based on farmer coordinates and haulage deductions.
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
- **Response (`200 OK`)**: Standard `ModelAppRecommendationResponse` with ranked list of mandis.

---

### 2.4 Asynchronous Mandi Recommendation Intake
- **Path**: `POST /api/v1/ai/recommend/async`
- **Description**: Enqueues recommendation request to background RabbitMQ queue.
- **Response (`202 Accepted`)**:
```json
{
  "success": true,
  "message": "Recommendation job accepted and queued",
  "data": {
    "job_id": "7b8f9e21-3a45-4c67-8d9e-0123456789ab",
    "status": "QUEUED",
    "operation": "RECOMMEND_MANDI",
    "created_at": "2026-09-03T12:00:00Z",
    "message": "Job successfully enqueued",
    "poll_url": "/api/v1/jobs/7b8f9e21-3a45-4c67-8d9e-0123456789ab"
  },
  "timestamp": "2026-09-03T12:00:00Z"
}
```

---

### 2.5 Poll Asynchronous Job Status
- **Path**: `GET /api/v1/ai/jobs/{jobId}`
- **Description**: Retrieves current status (`QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`) and computed result payload.
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Job status retrieved successfully",
  "data": {
    "job_id": "7b8f9e21-3a45-4c67-8d9e-0123456789ab",
    "operation": "RECOMMEND_MANDI",
    "status": "COMPLETED",
    "created_at": "2026-09-03T12:00:00Z",
    "completed_at": "2026-09-03T12:00:02Z",
    "result": {
      "recommended_mandi": "Bareilly",
      "net_return": 18570.0
    }
  },
  "timestamp": "2026-09-03T12:00:02Z"
}
```

---

### 2.6 Health & Readiness Probes
- `GET /api/v1/ai/health`: Returns Model-app process liveness status (`200 OK`).
- `GET /api/v1/ai/ready`: Returns external dependency readiness (`200 OK` if all dependencies UP, `503 Service Unavailable` if Redis or RabbitMQ offline).

---

## 3. Marketplace & Produce Lot Endpoints

| Endpoint | Method | Role | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/marketplace/lots` | `POST` | `ROLE_FARMER` | Create produce listing with crop, quantity, asking price, and optional location |
| `/api/v1/marketplace/lots/{id}/publish` | `POST` | `ROLE_FARMER` | Publish draft produce lot to public marketplace |
| `/api/v1/marketplace/lots` | `GET` | Public / Authenticated | Search active marketplace lots with filter by crop and market |
| `/api/v1/marketplace/lots/{id}/bids` | `POST` | `ROLE_BUYER` | Place competitive bid on published lot |
| `/api/v1/offers` | `POST` | `ROLE_BUYER` | Create direct binding purchase offer on a lot |
| `/api/v1/offers/{id}/accept` | `POST` | `ROLE_FARMER` | Farmer accepts buyer offer, transitioning lot to `ACCEPTED` |

---

## 4. Voice-Channel Telephony Endpoints (`/api/v1/voice`)

Designed for low-bandwidth feature-phone / IVR integration:
- `GET /api/v1/voice/prices`: Voice-synthesizer-friendly text response of latest modal price.
- `GET /api/v1/voice/offers`: Summarizes pending offers for farmer phone confirmation.
