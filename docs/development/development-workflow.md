# Development Workflow & Engineering Guidelines

## 1. Branching & Git Workflow

- **`main`**: Production-ready, stable codebase. Direct commits to `main` are restricted.
- **Feature Branches**: Named `feature/<description>` or `fix/<description>` (e.g. `feature/ai-query-routing`).
- **Commits**: Atomic, descriptive commits following Conventional Commits format (`feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`, `test: ...`).

---

## 2. Code Quality & Architectural Standards

### 2.1 Backend (Java / Spring Boot)
1. **SOLID Principles**:
   - **Single Responsibility (SRP)**: Controllers handle HTTP transport; Services handle business orchestration; Routers handle capability dispatch; Repositories handle persistence.
   - **Open/Closed (OCP)**: Extend capabilities via interfaces (`ModelAppClient`) and enums (`AiQueryIntent`) without altering existing client caller code.
   - **Dependency Inversion (DIP)**: Always inject abstractions; never couple services directly to HTTP transport classes (`RestClient`).
2. **Immutability & Value Objects**: Use Lombok `@Builder` and `@AllArgsConstructor` with defensive bounds checking (e.g. `Location.of(...)`).
3. **DTO Boundary Isolation**: Never return JPA `@Entity` classes directly from REST controllers; always map to DTOs in `dto/`.

### 2.2 Model-App (Python / FastAPI)
1. **Schema Validation**: All endpoint inputs and responses must be strongly typed using Pydantic v2 `BaseModel` classes with explicit field descriptions and validation constraints.
2. **Structured Logging**: Use the shared logger (`logger = get_logger(__name__)`) and never use naked `print()` statements.
3. **Async / Sync Decoupling**: CPU-bound operations (XGBoost inference) and network I/O must not block FastAPI's event loop. Heavy background tasks must be dispatched to the RabbitMQ consumer.

---

## 3. Testing Discipline

Before submitting pull requests, developers must execute local test suites:

### Running Core Backend Tests:
```bash
cd backend
./mvnw test
```
*Expected: 147 passed, 0 failures, 0 errors.*

### Running Model-App Tests:
```bash
cd Model-app
../.venv/bin/pytest tests/test_api_endpoints.py tests/test_job_service.py tests/test_phase1c_integration.py
```
*Expected: 50 passed, 0 failures across targeted suites.*

---

## 4. Strict Prohibitions & Anti-Patterns

1. **DO NOT Fabricate Data**: Never generate synthetic datasets, mock CSV feature files, or hardcode fake prices to force a failing test to pass.
2. **DO NOT Hardcode Secrets**: API keys (`DATA_GOV_API_KEY`), JWT secrets, and database credentials must never be committed to source files.
3. **DO NOT Call Model-App from Android Directly**: Core Backend is the sole gateway for Android clients.
4. **DO NOT Ask Ollama for Real-Time Prices**: Factual prices must always originate from AGMARKNET.
