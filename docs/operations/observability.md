# Observability, Tracing & System Probes

## 1. Distributed Request Tracing

MarketLink uses correlation IDs to maintain end-to-end auditability across microservice boundaries:

```
[Android Client]
      │
      │ HTTP Request [Optional X-Correlation-ID]
      ▼
[Core Backend: CorrelationIdFilter]
      ├── Preserves existing or generates new UUID
      ├── Stores in CorrelationIdContext (ThreadLocal)
      └── Adds to SLF4J MDC: org.slf4j.MDC.put("correlationId", id)
      │
      ▼
[Core Backend: HttpModelAppClient]
      ├── Injects header: "X-Correlation-ID": id
      │
      ▼
[Model-App: FastAPI Middleware]
      ├── Captures header from incoming request
      └── Injects into Python logging record: logger.bind(correlation_id=id)
      │
      ▼
[RabbitMQ Message Property]
      └── AMQP BasicProperties(correlation_id=id)
```

---

## 2. Health & Readiness Probes

### 2.1 Process Liveness Probe: `/health`
- **Purpose**: Verifies that the web server process is running, responsive, and accepting HTTP connections.
- **Used by**: Kubernetes Liveness Probes / Docker Healthchecks.
- **Endpoints**:
  - Core Backend: `GET /api/v1/ai/health`
  - Model-app: `GET /health`
- **Response**:
```json
{
  "status": "HEALTHY",
  "service": "marketlink-ai",
  "version": "1.0.0",
  "timestamp": "2026-09-03T12:00:00Z"
}
```

### 2.2 Dependency Readiness Probe: `/ready`
- **Purpose**: Verifies that external infrastructure dependencies are connected before routing user traffic.
- **Used by**: Kubernetes Readiness Probes / Load Balancer Target Health.
- **Evaluated Dependencies**:
  - `redis`: Pings Redis host on port `6379`.
  - `rabbitmq`: Tests AMQP socket handshake on port `5672`.
  - `ml_predictor`: Verifies in-memory model registry state.
- **Behavior**:
  - If **ALL** dependencies are connected: returns **HTTP 200 OK** (`"status": "READY"`).
  - If **ANY** dependency is disconnected: returns **HTTP 503 Service Unavailable** (`"status": "NOT_READY"`).
- **Response (`503 Service Unavailable`)**:
```json
{
  "ready": false,
  "status": "NOT_READY",
  "dependencies": {
    "redis": {"available": false, "status": "DOWN"},
    "rabbitmq": {"available": false, "status": "DOWN"},
    "ml_predictor": {"available": true, "status": "UP"}
  },
  "timestamp": "2026-09-03T12:00:00Z"
}
```
