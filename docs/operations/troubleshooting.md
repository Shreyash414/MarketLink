# Operational Troubleshooting Guide

This guide provides diagnostics and safe resolutions for 12 common operational and runtime failure scenarios.

---

## 1. Core Backend Cannot Reach Model-App
- **Symptom**: Core Backend returns `HTTP 503 Service Unavailable` with message `"AI service connection refused or unreachable"`.
- **Likely Cause**: Model-app is not running, running on an unexpected port, or firewalled.
- **Diagnostic Check**:
  ```bash
  curl -i http://localhost:8000/health
  netstat -tuln | grep 8000
  ```
- **Safe Resolution**:
  Start the Model-app Uvicorn server:
  ```bash
  cd Model-app && ../.venv/bin/uvicorn src.main:app --port 8000
  ```
  Ensure `MODEL_APP_BASE_URL=http://localhost:8000` is set in Core Backend's `.env`.

---

## 2. Model-App Unavailable / Unready (`503 Service Unavailable`)
- **Symptom**: `GET /ready` returns `HTTP 503` with `"status": "NOT_READY"`.
- **Likely Cause**: Redis or RabbitMQ are not running locally.
- **Diagnostic Check**: Inspect the `dependencies` object in the `/ready` response.
- **Safe Resolution**:
  Start the offline service (e.g. `sudo systemctl start redis-server` or `sudo systemctl start rabbitmq-server`). Note that Model-app process can run independently and serve `/health` and `/market-data` even when queues are offline.

---

## 3. Redis Service Unavailable
- **Symptom**: Submitting asynchronous jobs returns `HTTP 503` with `"Redis is not reachable"`.
- **Likely Cause**: Redis server daemon stopped or port `6379` blocked.
- **Diagnostic Check**:
  ```bash
  redis-cli ping
  ```
- **Safe Resolution**:
  Restart Redis: `sudo systemctl restart redis-server`. Verify connection credentials if `REDIS_PASSWORD` is configured.

---

## 4. RabbitMQ Service Unavailable
- **Symptom**: Submitting async jobs fails with `"RabbitMQ broker connection refused"`.
- **Likely Cause**: RabbitMQ daemon offline or guest credentials rejected.
- **Diagnostic Check**:
  ```bash
  sudo rabbitmqctl status
  ```
- **Safe Resolution**:
  Start RabbitMQ: `sudo systemctl start rabbitmq-server`. Verify AMQP port `5672` is listening.

---

## 5. Ollama LLM Service Offline
- **Symptom**: Farmer general query returns `HTTP 503` with `"Ollama service is currently unavailable"`.
- **Likely Cause**: Local Ollama server is not running on port `11434`.
- **Diagnostic Check**:
  ```bash
  curl -s http://localhost:11434/api/version
  ```
- **Safe Resolution**:
  Start Ollama in a separate terminal:
  ```bash
  ollama serve
  ```
  Verify model presence: `ollama list` (ensure `llama3` is downloaded via `ollama pull llama3`).

---

## 6. data.gov.in API Timeout
- **Symptom**: Fetching live market data yields cached records with warning `"API request failed on attempt 1/2: Read timed out"`.
- **Likely Cause**: Upstream government server rate limiting or latency spike.
- **Diagnostic Check**: Review Model-app logs for `Read timed out. (read timeout=5)`.
- **Safe Resolution**:
  System automatically falls back to local cache (`data_source: "CACHE"`). No action needed. If persistent, check whether `DATA_GOV_API_KEY` quota is exhausted on the Open Government Data portal.

---

## 7. Missing Model Feature CSV (`ARTIFACT_MISSING`)
- **Symptom**: Model prediction returns error `"Required feature CSV artifact not found for commodity..."`.
- **Likely Cause**: Companion feature CSV files were omitted from the training export.
- **Diagnostic Check**:
  Check if `Model-app/data/processed/models/change_xgboost_v3/final/bareilly_final_features.csv` exists.
- **Safe Resolution**:
  > [!WARNING]
  > **Do NOT Fabricate Fake Data**: Do not create dummy CSV files. This is a known, deferred deployment gap. The ML training team will furnish real companion feature artifacts during final deployment packaging.

---

## 8. Unknown Job ID (`404 Not Found`)
- **Symptom**: Polling `GET /api/v1/ai/jobs/{jobId}` returns `404 Not Found`.
- **Likely Cause**: Job ID UUID does not exist in Redis, or expired past the 24-hour TTL.
- **Diagnostic Check**: Check Redis key presence: `redis-cli EXISTS job:{jobId}`.
- **Safe Resolution**: Resubmit the recommendation request via `POST /api/v1/ai/recommend/async` to obtain a fresh active job ID.

---

## 9. Invalid Coordinates (`422 Unprocessable Entity`)
- **Symptom**: Mandi recommendation returns `422` with message `"Farmer location coordinates (latitude and longitude) are required"`.
- **Likely Cause**: Request omitted `location` or supplied coordinates outside valid ranges.
- **Diagnostic Check**: Verify latitude is in $[-90.0, 90.0]$ and longitude is in $[-180.0, 180.0]$.
- **Safe Resolution**: Supply accurate coordinates from mobile GPS. Do not default to `(0,0)`.

---

## 10. CORS Rejection
- **Symptom**: Web client or Swagger UI fails to connect with browser CORS error.
- **Likely Cause**: Request origin not registered in Core Backend's `CorsConfiguration`.
- **Diagnostic Check**: Inspect `Access-Control-Allow-Origin` response header in browser developer tools.
- **Safe Resolution**: Add development frontend URL (e.g. `http://localhost:3000`) to `SecurityConfig.java`.

---

## 11. JWT Authentication Failure (`401 Unauthorized`)
- **Symptom**: Request rejected with `401 Unauthorized` and `"Full authentication is required"`.
- **Likely Cause**: Missing `Authorization: Bearer <token>` header, or token signature expired.
- **Diagnostic Check**: Decode token using `jwt.io` to inspect expiration claim (`exp`).
- **Safe Resolution**: Call `/api/v1/auth/login` to obtain a fresh token and pass in the `Authorization` header.

---

## 12. Missing Environment Variables
- **Symptom**: Application fails during startup with `IllegalArgumentException` or missing configuration property.
- **Likely Cause**: `.env` file absent or variable name misspelled.
- **Diagnostic Check**: Compare local `.env` with `.env.example`.
- **Safe Resolution**: Populate missing keys in `.env` using `.env.example` as a template.
