# MarketLink Documentation Portal

Welcome to the technical documentation repository for **MarketLink (SIH Problem Statement 26132: Strengthening Market Linkages and Price Discovery for Farmers)**.

This portal provides authoritative, architecture-accurate, and internally consistent documentation reflecting the current implemented state of MarketLink across its microservices, domain models, AI/ML pipelines, and integration boundaries.

---

## Documentation Directory Map

```
docs/
├── README.md                              # This navigation index
│
├── architecture/
│   ├── system-architecture.md             # End-to-end multi-tier architecture & data flow
│   ├── core-backend-architecture.md       # Spring Boot 3.3 gateway, controllers, domain models
│   ├── model-app-architecture.md          # FastAPI service, XGBoost, Ollama, Redis, RabbitMQ
│   ├── integration-architecture.md        # HTTP client, X-Correlation-ID, timeouts, exceptions
│   └── ai-query-routing.md                # Deterministic query routing taxonomy & classifier
│
├── api/
│   ├── core-backend-api.md                # Core Backend REST endpoints & Swagger reference
│   ├── model-app-api.md                   # Model-app internal REST endpoints
│   ├── ai-query-api.md                    # Deep-dive on natural language query endpoint (/api/v1/ai/query)
│   └── error-handling.md                  # Unified error envelopes, status codes, sanitization
│
├── ai-ml/
│   ├── overview.md                        # AI/ML subsystem overview and design rationale
│   ├── model-pipeline.md                  # XGBoost model artifacts and feature requirements
│   ├── query-routing.md                   # Heuristics, regex rules, Hinglish handling
│   ├── market-data.md                     # AGMARKNET live ingestion, cache fallback, API keys
│   ├── price-prediction.md                # Price forecasting, confidence intervals, quality gate
│   ├── mandi-recommendation.md            # Haversine distance, haulage economics, net returns
│   └── ollama.md                          # Ollama LLM integration, prompts, controlled failures
│
├── development/
│   ├── setup.md                           # Local developer onboarding & runtime setup
│   ├── configuration.md                   # Environment variables & application.yml reference
│   ├── project-structure.md               # Detailed directory tree & module responsibilities
│   └── development-workflow.md            # Git guidelines, pair programming, code standards
│
├── security/
│   ├── security-architecture.md           # Stateless JWT, authorization policies, CORS
│   └── secrets-and-configuration.md       # Secret handling, .env management, git hygiene
│
├── operations/
│   ├── deployment.md                      # Topology, multi-tier containers, async workers
│   ├── observability.md                   # Correlation IDs, MDC logging, health & readiness
│   └── troubleshooting.md                 # 12 common runtime issues, diagnosis & safe resolutions
│
├── testing/
│   ├── testing-strategy.md                # Testing philosophy, MockMvc, MockRestServiceServer, pytest
│   └── test-status.md                     # Authoritative baseline test verification report
│
└── decisions/
    └── architecture-decisions.md          # Architecture Decision Records (ADRs 001 - 007)
```

---

## Quick Navigation by Role

| Target Audience | Recommended Entry Points |
| :--- | :--- |
| **New Developers / Contributors** | [Development Setup](development/setup.md), [Project Structure](development/project-structure.md), [Configuration](development/configuration.md) |
| **Backend Developers (Spring Boot)** | [Core Backend Architecture](architecture/core-backend-architecture.md), [Integration Architecture](architecture/integration-architecture.md), [Core Backend API](api/core-backend-api.md) |
| **AI / ML Engineers (Python / FastAPI)** | [Model-App Architecture](architecture/model-app-architecture.md), [AI/ML Overview](ai-ml/overview.md), [Model Pipeline](ai-ml/model-pipeline.md), [Market Data](ai-ml/market-data.md) |
| **Android / Client Engineers** | [AI Query API](api/ai-query-api.md), [Core Backend API](api/core-backend-api.md), [Error Handling](api/error-handling.md) |
| **DevOps / Reviewers / Judges** | [System Architecture](architecture/system-architecture.md), [Architecture Decisions (ADRs)](decisions/architecture-decisions.md), [Test Status](testing/test-status.md) |
