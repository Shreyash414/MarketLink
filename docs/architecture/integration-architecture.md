# Core Backend ↔ Model-App Integration Architecture

## 1. Overview & Integration Principles

The communication between the Spring Boot Core Backend and the FastAPI Model-app is designed as a secure, production-grade private HTTP integration layer.

### Key Architectural Tenets:
1. **Model-app is an Internal Service**: Android and external clients **never** connect directly to Model-app.
2. **Dedicated Contract Isolation**: Core Backend uses dedicated DTOs in `com.marketlink.backend.ai.dto.modelapp`. Zero JPA database entities or raw internal maps are leaked over the boundary.
3. **Explicit Configurable Timeouts**: Network operations are governed by strict connect, read, and query timeouts.
4. **End-to-End Correlation Tracking**: Inbound correlation IDs are captured and injected into all outbound HTTP headers via `X-Correlation-ID`.
5. **Sanitized Domain Exception Translation**: Upstream HTTP errors are mapped into domain exceptions extending `ApiException` with zero leakage of internal server paths or infrastructure credentials.

---

## 2. Interface Abstraction: `ModelAppClient`

To adhere to the Dependency Inversion Principle, business services depend exclusively on the `ModelAppClient` interface, rather than Spring's `RestClient` directly:

```java
package com.marketlink.backend.ai.client;

import com.marketlink.backend.ai.dto.modelapp.*;
import java.util.List;

public interface ModelAppClient {
    ModelAppHealthResponse checkHealth();
    ModelAppReadinessResponse checkReadiness();
    ModelAppPredictionResponse predictPrice(ModelAppPredictionRequest request);
    ModelAppRecommendationResponse getRecommendation(ModelAppRecommendationRequest request);
    ModelAppAsyncJobAcceptedResponse submitAsyncRecommendation(ModelAppRecommendationRequest request);
    ModelAppJobStatusResponse getJobStatus(String jobId);
    ModelAppQueryResponse processGeneralQuery(ModelAppQueryRequest request);
    ModelAppMarketDataResponse getMarketData(String commodity, List<String> markets, String state, Integer limit);
}
```

---

## 3. Concrete Implementation: `HttpModelAppClient`

Located at `com.marketlink.backend.ai.client.HttpModelAppClient`.

### 3.1 Timeout Configuration
Timeouts are configured on the underlying `SimpleClientHttpRequestFactory` via `ModelAppProperties`:
```yaml
marketlink:
  model-app:
    base-url: ${MODEL_APP_BASE_URL:http://localhost:8000}
    connect-timeout-ms: ${MODEL_APP_CONNECT_TIMEOUT_MS:5000}
    read-timeout-ms: ${MODEL_APP_READ_TIMEOUT_MS:15000}
    query-timeout-ms: ${MODEL_APP_QUERY_TIMEOUT_MS:30000}
```

### 3.2 Correlation ID Propagation
```java
String correlationId = CorrelationIdContext.getCorrelationId();

modelAppRestClient.post()
    .uri("/api/v1/predict")
    .header(CorrelationIdContext.CORRELATION_ID_HEADER, correlationId)
    .contentType(MediaType.APPLICATION_JSON)
    .body(request)
    .retrieve()
    .body(ModelAppPredictionResponse.class);
```

---

## 4. Exception Mapping & Error Translation

All HTTP operations are wrapped by an execution interceptor that translates HTTP status codes and network faults into the Core Backend domain exception hierarchy:

| Model-app Status / Network Fault | Core Backend Domain Exception | Resulting Public HTTP Status | Log Level | Client Message |
| :--- | :--- | :--- | :--- | :--- |
| **HTTP 400 Bad Request** | `ModelAppValidationException` | `400 Bad Request` | `WARN` | Extracted `error.message` / `detail` |
| **HTTP 404 Not Found** | `ModelAppNotFoundException` | `404 Not Found` | `WARN` | Extracted `error.message` (e.g. Job not found) |
| **HTTP 422 Unprocessable Entity** | `ModelAppValidationException` | `422 Unprocessable` | `WARN` | Validation constraint description |
| **HTTP 500 Internal Server Error** | `ModelAppException` | `500 Internal Error` | `ERROR` | Sanitized server error message |
| **HTTP 502 Bad Gateway** | `ModelAppBadGatewayException` | `502 Bad Gateway` | `ERROR` | Upstream AI engine error (e.g. Ollama failed) |
| **HTTP 503 Service Unavailable** | `ModelAppUnavailableException` | `503 Service Unavail`| `WARN` | AI model service is temporarily offline |
| **Socket Read Timeout** | `ModelAppTimeoutException` | `504 Gateway Timeout`| `ERROR` | Model-app request timed out |
| **Connection Refused / Network Down** | `ModelAppUnavailableException`| `503 Service Unavail`| `ERROR` | AI service connection refused or unreachable |

### 4.1 Information Sanitization Guarantees
- **Stack Traces**: Suppressed from client response bodies.
- **Internal Paths**: Paths such as `/home/shreyash/.../features.csv` are stripped or normalized to high-level error codes (`ARTIFACT_MISSING`).
- **Internal URLs**: Private URLs (`http://localhost:8000`, `amqp://...`) are never displayed to the client.
