# FastAPI Model-App Architecture

## 1. Overview & Technologies

The MarketLink Model-app is an asynchronous AI/ML and data orchestration microservice built on **FastAPI** and **Python 3.14**. It is responsible for price predictions, mandi recommendations, live market data ingestion, background job queueing, and local LLM trade advisory.

### Technology Stack:
- **Framework**: FastAPI 0.115+, Starlette, Pydantic v2
- **ASGI Server**: Uvicorn
- **ML Engines**: XGBoost Regressors, Scikit-learn, Pandas, NumPy
- **Asynchronous Storage**: Redis 7 (`redis-py`)
- **Message Broker**: RabbitMQ (`pika`)
- **LLM Integration**: Ollama REST client (local LLaMA 3 runtime)
- **External Ingestion**: data.gov.in AGMARKNET REST API (`requests` with exponential retry)

---

## 2. Directory Structure & Subsystem Layout

```
Model-app/src/
├── api/
│   ├── routes/
│   │   ├── health.py                      # /health and /ready probes
│   │   ├── market_data.py                 # /api/v1/market-data
│   │   ├── predictions.py                 # /api/v1/predict
│   │   ├── queries.py                     # /api/v1/query (Ollama advisory)
│   │   ├── recommendations.py             # /api/v1/recommend and /recommend/async
│   │   └── jobs.py                        # /api/v1/jobs/{job_id}
│   └── schemas/                           # Pydantic v2 validation contracts
├── core/
│   ├── config.py                          # Pydantic settings & environment bindings
│   ├── exceptions.py                      # Model-app domain exceptions
│   └── logging.py                         # Structured logging configuration
├── data/
│   ├── ingestion/                         # CurrentDataFetcher (data.gov.in)
│   └── processing/                        # HistoricalDataFetcher & HistoricalMerger
├── messaging/
│   ├── rabbitmq_publisher.py              # AMQP publisher with persistent delivery
│   └── rabbitmq_worker.py                 # Background consumer & job processor
├── models/
│   ├── model_predictor.py                 # XGBoost inference & confidence calculation
│   └── model_registry.py                  # Model registry & artifact preloading
├── recommendation/
│   ├── mandi_recommender.py               # Haversine distance & haulage economics
│   └── economics.py                       # Net return & transport fee calculation
├── repositories/
│   └── redis_job_repository.py            # Redis atomic job state persistence
├── services/
│   ├── job_service.py                     # Job lifecycle coordinator
│   ├── market_data_service.py             # Market data caching & aggregation
│   └── ollama_service.py                  # Controlled Ollama LLM integration
└── main.py                                # Application entry point & lifespan manager
```

---

## 3. Endpoints Reference

| Endpoint | Method | Purpose | Sync / Async | Data Source |
| :--- | :--- | :--- | :--- | :--- |
| `/health` | `GET` | Process liveness probe | Sync | Internal process state |
| `/ready` | `GET` | Dependency readiness probe (Redis, RabbitMQ, ML models) | Sync | Active dependency pings |
| `/api/v1/market-data` | `GET` | Daily AGMARKNET mandi prices and arrivals | Sync | data.gov.in API / local cache |
| `/api/v1/predict` | `POST` | Next-day modal price forecast for commodity in market | Sync | XGBoost model |
| `/api/v1/recommend` | `POST` | Geospatial mandi recommendation with ranked net returns | Sync | MandiRecommender + MarketData |
| `/api/v1/recommend/async`| `POST` | Asynchronous recommendation job submission | Async (202) | Enqueued to RabbitMQ + Redis |
| `/api/v1/jobs/{job_id}` | `GET` | Retrieve asynchronous AI job status and payload | Sync | Redis job store |
| `/api/v1/query` | `POST` | Natural language agricultural advisory | Sync | Ollama LLM |

---

## 4. Subsystem Details

### 4.1 Market Data Pipeline (`MarketDataService`)
- Queries official government AGMARKNET feeds via `CurrentDataFetcher` using `DATA_GOV_API_KEY`.
- Implements resilient timeout handling (5-second socket timeout, 2 retry attempts with exponential backoff).
- Caches recent observations in local JSON storage to gracefully support offline or degraded network conditions.
- Tagged with `data_source: "LIVE"`, `"CACHE"`, or `"ERROR"`.

### 4.2 ML Prediction Pipeline (`ModelPredictor`)
- Hosts trained XGBoost regression models for supported commodity-market pairs (e.g. Onion:Bareilly, Onion:Nagpur, Potato:Agra, Tomato:Kolar, Wheat:Khanna, Rice:Burdwan).
- Generates:
  - `predicted_price`: Next-day expected modal price.
  - `expected_change`: Absolute difference from current price.
  - `expected_direction`: `UP`, `DOWN`, or `STABLE`.
  - `confidence_intervals`: Lower and upper bounds based on historical RMSE.
  - `reliability_score`: Quantitative quality metric (0–100%).
  - `quality_class`: `STRONG`, `MODERATE`, or `WEAK`.

### 4.3 Mandi Recommendation Engine (`MandiRecommender`)
- Evaluates candidate mandis within search radius (`max_distance_km`, default 200 km) from farmer coordinates.
- Calculates Haversine great-circle distance between farmer `(lat, lon)` and mandi coordinates.
- Applies economic formula:
  $$\text{Gross Revenue} = \text{Quantity (Quintals)} \times \text{Modal Price}$$
  $$\text{Transport Cost} = \text{Distance (km)} \times \text{Quantity (Quintals)} \times \text{Base Rate per Quintal-km}$$
  $$\text{Market Fee} = \text{Gross Revenue} \times \text{Mandi Cess Percentage}$$
  $$\text{Net Return} = \text{Gross Revenue} - (\text{Transport Cost} + \text{Market Fee})$$
- Ranks mandis in descending order of Net Return.

### 4.4 Ollama LLM Advisory (`OllamaService`)
- Connects to local Ollama runtime on `http://localhost:11434`.
- Employs domain-specific system prompt restricting responses to agronomy, crop protection, and post-harvest storage.
- **Strictly Non-Authoritative for Prices**: Never invents or answers factual mandi prices or numerical forecasts.
- **Controlled Failure**: Returns structured HTTP 502/503 errors if Ollama is unreachable or returns empty responses.

---

## 5. Asynchronous Job Lifecycle & Persistence

```
Client (Core Backend)
      │  POST /api/v1/recommend/async
      ▼
JobService.create_job()
      │
      ├──> Redis: HSET job:{id} -> {status: "QUEUED", created_at: "..."}
      │
      └──> RabbitMQ: BasicPublish -> exchange: "ai.direct", queue: "ai.recommendations"
      │
      ▼ Returns HTTP 202 Accepted {job_id: "...", poll_url: "/api/v1/jobs/..."}

─────────────────────── ASYNC WORKER EXECUTION ───────────────────────

RabbitMQWorker.on_message()
      │
      ├──> Redis: HSET job:{id} -> {status: "PROCESSING"}
      │
      ├──> MandiRecommender.recommend()
      │       ├── SUCCESS: Redis: HSET job:{id} -> {status: "COMPLETED", result: {...}}
      │       └── FAILURE: Redis: HSET job:{id} -> {status: "FAILED", error: "..."}
      │
      └──> RabbitMQ: BasicAck(delivery_tag)
```

- **Atomic State Transitions**: Ensures idempotency and race-condition prevention across concurrent consumers.
- **TTL Persistence**: Redis job entries are retained with a 24-hour TTL for subsequent client polling.
