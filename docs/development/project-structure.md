# Repository Layout & Project Structure

## 1. Complete Repository Directory Tree

```
MarketLink/
├── README.md                              # Root project entry point and high-level architecture
├── .env.example                           # Template environment configuration file
├── .gitignore                             # Git ignore policies (ignores .env, target/, .venv/, etc.)
│
├── docs/                                  # Centralized Technical & Architecture Documentation
│   ├── README.md                          # Documentation index
│   ├── architecture/                      # Multi-tier system, core backend, model-app, routing
│   ├── api/                               # Core backend API, model-app API, query API, error handling
│   ├── ai-ml/                             # ML pipelines, query routing, market data, Ollama
│   ├── development/                       # Developer setup, configuration, workflow
│   ├── security/                          # Security architecture and secret handling
│   ├── operations/                        # Deployment topology, observability, troubleshooting
│   ├── testing/                           # Testing strategy and authoritative test verification status
│   └── decisions/                         # Architecture Decision Records (ADRs)
│
├── backend/                               # Spring Boot Core Backend Service
│   ├── pom.xml                            # Maven build definition (Spring Boot 3.3.3, Java 21)
│   ├── mvnw / mvnw.cmd                    # Apache Maven wrapper scripts
│   ├── src/main/resources/
│   │   └── application.yml                # Main application configuration & environment overrides
│   ├── src/main/java/com/marketlink/backend/
│   │   ├── ai/                            # AI subsystem & integration
│   │   │   ├── classifier/                # AiQueryClassifier (deterministic intent engine)
│   │   │   ├── client/                    # ModelAppClient interface & HttpModelAppClient
│   │   │   ├── config/                    # ModelAppProperties & RestClient builder
│   │   │   ├── controller/                # AiAdvisoryController (/api/v1/ai/**)
│   │   │   ├── dto/
│   │   │   │   ├── modelapp/              # Strict DTO contracts matching Model-app schemas
│   │   │   │   └── query/                 # AiNaturalLanguageQueryRequest & AiQueryResponse
│   │   │   ├── enums/                     # AiQueryIntent enum
│   │   │   ├── exception/                 # ModelAppException hierarchy
│   │   │   ├── router/                    # AiQueryRouter capability orchestrator
│   │   │   └── service/                   # AiAdvisoryService application coordinator
│   │   ├── auth/                          # User registration, login, JWT issuance
│   │   ├── common/                        # Cross-cutting concerns
│   │   │   ├── context/                   # CorrelationIdContext (ThreadLocal + MDC)
│   │   │   ├── exception/                 # ApiException & GlobalExceptionHandler
│   │   │   ├── filter/                    # CorrelationIdFilter
│   │   │   └── response/                  # ApiResponse<T> & ErrorResponse
│   │   ├── domain/                        # Domain entities & value objects
│   │   │   ├── common/entity/             # Location.java (@Embeddable coordinates)
│   │   │   ├── market/entity/             # Market.java
│   │   │   ├── marketplace/entity/        # Lot.java, LotProduce.java, Bid.java
│   │   │   └── user/entity/               # User.java, FarmerProfile.java, BuyerProfile.java
│   │   ├── marketplace/                   # Lot management & buyer bidding service
│   │   ├── offer/                         # Direct purchase offer & acceptance lifecycle
│   │   ├── security/                      # Spring Security filter chain & policies
│   │   └── voice/                         # Telephony / IVR channel adapters
│   └── src/test/java/com/marketlink/backend/
│       ├── ai/                            # Client, router, classifier, service, controller tests
│       ├── domain/                        # LocationTest boundary suite
│       └── security/                      # Authorization & security integration tests
│
└── Model-app/                             # FastAPI AI/ML & Ingestion Microservice
    ├── requirements.txt                   # Python dependencies (FastAPI, XGBoost, Redis, Pika)
    ├── README.md                          # Microservice developer documentation
    ├── src/
    │   ├── main.py                        # FastAPI application entry & startup lifespan
    │   ├── api/
    │   │   ├── routes/                    # API routers (predict, recommend, jobs, query, market_data)
    │   │   └── schemas/                   # Pydantic v2 schemas
    │   ├── core/                          # Settings (pydantic-settings), structured logging
    │   ├── data/
    │   │   ├── ingestion/                 # CurrentDataFetcher (data.gov.in AGMARKNET feed)
    │   │   └── processing/                # HistoricalDataFetcher & data mergers
    │   ├── messaging/                     # RabbitMQ publisher and background consumer worker
    │   ├── models/                        # XGBoost ModelPredictor and ModelRegistry
    │   ├── recommendation/                # MandiRecommender & Haversine haulage economics
    │   ├── repositories/                  # RedisJobRepository (atomic job state storage)
    │   └── services/                      # JobService, MarketDataService, OllamaService
    ├── tests/                             # Pytest test suites (151 tests)
    └── data/                              # Pre-trained XGBoost JSON models & mandi coordinates
```

---

## 2. Directory Responsibilities Summary

| Directory | Responsibility | Primary Stack |
| :--- | :--- | :--- |
| `backend/src/main/java/.../ai/` | Natural-language query parsing, capability routing, and HTTP client integration with Model-app. | Java 21, Spring 6 `RestClient` |
| `backend/src/main/java/.../domain/` | JPA persistence entities and domain value objects (`Location`). | Jakarta Persistence, Hibernate |
| `backend/src/main/java/.../marketplace/` | Direct farmer listing, lot management, and buyer bidding. | Spring Data JPA, Transactions |
| `Model-app/src/api/` | Internal REST endpoints exposing ML, recommendations, and jobs. | FastAPI, Pydantic v2 |
| `Model-app/src/models/` | XGBoost regressor loading, inference, and quality gating. | XGBoost, Scikit-learn, Pandas |
| `Model-app/src/recommendation/` | Geospatial Haversine calculation and economic net-return ranking. | NumPy, Python Math |
| `Model-app/src/messaging/` | AMQP publisher and consumer workers for asynchronous jobs. | RabbitMQ, Pika |
| `Model-app/src/repositories/` | Atomic job state persistence and caching. | Redis 7, `redis-py` |
| `Model-app/src/data/` | Live AGMARKNET API ingestion and local JSON fallback caching. | Requests, Python JSON |
