# Testing Strategy & Verification Methodology

## 1. Testing Philosophy

MarketLink enforces a rigorous, multi-tier testing strategy designed to achieve high code quality, zero regression, and rapid local iteration without requiring expensive external live services.

### Core Principles:
1. **Hermetic Unit & Component Isolation**: Unit tests must never depend on live internet connectivity, active cloud APIs, or third-party infrastructure.
2. **Deterministic Reproducibility**: Tests must pass consistently across developer workstations and CI runners.
3. **Boundary Verification**: Boundary invariants (such as coordinate limits $[-90, 90]$ and timeout triggers) are verified with explicit boundary test suites.
4. **Transparent Defect Reporting**: Test failures due to external dependencies or deferred artifacts are documented transparently rather than artificially bypassed.

---

## 2. Testing Layers & Tooling

```
Level 1: Domain & Unit Tests
  ├── LocationTest (Geospatial coordinate boundary validation)
  ├── AiQueryClassifierTest (Deterministic regex intent & Hinglish tests)
  └── Pytest ML Model Quality & Registry Tests

Level 2: Mock Client & Service Integration Tests
  ├── HttpModelAppClientTest (MockRestServiceServer testing all 17 HTTP scenarios)
  ├── AiQueryRouterTest (Mockito capability isolation tests)
  └── Pytest Redis Repository & RabbitMQ Messaging Mocks

Level 3: Controller & Gateway Integration Tests
  ├── AiAdvisoryControllerTest (MockMvc testing /api/v1/ai/** routes & error mapping)
  ├── PrototypeAuthorizationSecurityTest (Spring Security role policy verification)
  └── Pytest FastAPI TestClient API Endpoint Suites
```

---

## 3. Test Tools & Frameworks

### 3.1 Spring Boot Backend
- **JUnit 5 (Jupiter)**: Test lifecycle and assertions.
- **Mockito 5**: Service mocking and interaction verification (`verify(client, never()).predict(...)`).
- **Spring Test (`MockRestServiceServer`)**: Binds directly to Spring 6's `RestClient.Builder` to simulate all Model-app responses (200, 202, 400, 404, 422, 500, 502, 503, timeouts, correlation headers) without opening external sockets.
- **Spring Test (`MockMvc`)**: Tests REST controllers with `GlobalExceptionHandler` to verify JSON envelopes and HTTP status codes.

### 3.2 FastAPI Model-App
- **`pytest`**: Python test runner with discovery and reporting.
- **`pytest-mock`**: Isolates Redis and Pika connections in unit suites.
- **`fastapi.testclient.TestClient`**: In-process ASGI test client testing endpoint routing and schema validation.
