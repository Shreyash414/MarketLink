# Complete System Architecture

## 1. Architectural Overview

MarketLink is designed as a distributed, decoupled multi-tier system engineered to bridge agricultural direct selling with intelligent trade insights. The system enforces strict separation of concerns across presentation, domain orchestration, AI/ML inference, and asynchronous task execution.

```mermaid
graph TB
    subgraph "External Clients"
        Android["Android Mobile App<br/>(Kotlin / Retrofit)"]
        Voice["Voice / IVR Channel<br/>(Telephony Adapter)"]
    end

    subgraph "Edge / Ingress Gateway"
        Filter["CorrelationIdFilter<br/>(X-Correlation-ID)"]
        Security["Spring Security<br/>(Stateless JWT Auth)"]
    end

    subgraph "Spring Boot Core Backend (Port 8080)"
        Controller["AiAdvisoryController<br/>(REST API Boundary)"]
        Service["AiAdvisoryService<br/>(Domain Orchestration)"]
        Router["AiQueryRouter<br/>(Workflow Execution)"]
        Classifier["AiQueryClassifier<br/>(Deterministic Intent Engine)"]
        Client["HttpModelAppClient<br/>(Spring 6 RestClient)"]
        
        DB_JPA[("PostgreSQL / H2<br/>Business DB")]
        DB_Mongo[("MongoDB<br/>Produce Images")]
    end

    subgraph "FastAPI Model-app (Port 8000)"
        API_GW["FastAPI Router<br/>(Asynchronous ASGI)"]
        MarketSvc["MarketDataService<br/>(AGMARKNET Pipeline)"]
        PredictSvc["ModelPredictor<br/>(XGBoost Inferencing)"]
        Recommender["MandiRecommender<br/>(Haversine Haulage Model)"]
        OllamaSvc["OllamaService<br/>(Controlled LLM Client)"]
        JobSvc["JobService<br/>(Lifecycle Manager)"]
        
        Worker["Background Consumer<br/>(RabbitMQ Worker)"]
    end

    subgraph "Supporting Infrastructure"
        Redis[("Redis 7<br/>Job Store & Cache")]
        RabbitMQ[["RabbitMQ<br/>AMQP Queue: ai.recommendations"]]
        DataGov["data.gov.in API<br/>(Official Agmarknet Feed)"]
        Ollama["Ollama Runtime<br/>(Local LLaMA 3 Daemon)"]
    end

    Android -->|HTTPS / REST + JWT| Filter
    Voice -->|HTTPS / REST| Filter
    Filter --> Security
    Security --> Controller
    Controller --> Service
    Service --> Router
    Router --> Classifier
    Router --> Client

    Controller --> DB_JPA
    Controller --> DB_Mongo

    Client -->|HTTP / JSON<br/>Timeout: 5s/15s/30s<br/>X-Correlation-ID| API_GW

    API_GW --> MarketSvc
    API_GW --> PredictSvc
    API_GW --> Recommender
    API_GW --> OllamaSvc
    API_GW --> JobSvc

    MarketSvc --> DataGov
    OllamaSvc --> Ollama
    JobSvc --> Redis
    JobSvc --> RabbitMQ

    RabbitMQ -.->|Dispatch| Worker
    Worker --> Recommender
    Worker --> Redis
```

---

## 2. Component Responsibility Matrix

| Component | Primary Responsibility | Strict Boundaries (Must NOT Do) |
| :--- | :--- | :--- |
| **Android Client** | User interface, farmer input capture, camera produce photos, JWT presentation. | **Must NOT** access Model-app, Redis, RabbitMQ, or Ollama directly. |
| **Core Backend Gateway** | Public ingress, JWT authentication, request validation, domain persistence, correlation tracking. | **Must NOT** implement XGBoost inference, mandi distance algorithms, or call Ollama directly. |
| **AiAdvisoryController** | Thin HTTP REST boundary, `@Valid` validation, OpenAPI 3 annotations. | **Must NOT** contain business logic, query classification, or direct HTTP client invocations. |
| **AiAdvisoryService** | Business coordination, farmer profile integration, service delegation. | **Must NOT** manipulate raw HTTP requests, construct URLs, or serialize JSON. |
| **AiQueryClassifier** | Deterministic intent parsing (English + Hinglish), confidence estimation, entity extraction. | **Must NOT** invoke external LLMs merely to classify intent. |
| **AiQueryRouter** | Multi-capability routing, combining ML forecasts with geospatial mandi ranking. | **Must NOT** perform inference calculations inside Java; delegates to `ModelAppClient`. |
| **HttpModelAppClient** | Internal HTTP transport, connection/read timeouts, `X-Correlation-ID` header injection, sanitized exception translation. | **Must NOT** leak raw upstream error JSON or expose internal server filesystem paths to callers. |
| **FastAPI Model-app** | AI/ML inference, government data caching, local LLM integration, async job queue. | **Must NOT** handle user authentication, buyer-farmer lot lifecycle, or direct client billing. |
| **ModelPredictor** | XGBoost next-day modal price predictions, confidence intervals, model quality gating. | **Must NOT** fabricate predictions when required feature CSV files are absent. |
| **MandiRecommender** | Haversine distance, transportation haulage economics, mandi fee deduction, net returns. | **Must NOT** invent coordinates when farmer location is missing. |
| **OllamaService** | General agricultural advisory (cultivation, agronomy, storage, pest advice). | **Must NOT** hallucinate factual spot market prices or numerical forecasts. |
| **Redis 7** | Shared transient cache, atomic job state transitions (`QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`). | **Must NOT** be treated as a permanent relational business store. |
| **RabbitMQ** | Reliable asynchronous job delivery with persistent queues and consumer acknowledgements. | **Must NOT** execute computation directly; acts purely as message broker. |

---

## 3. End-to-End Sequence Diagrams

### 3.1 Synchronous Natural Language AI Query Flow
```mermaid
sequenceDiagram
    autonumber
    actor Farmer as Android Farmer Client
    participant Core as Core Backend (Spring Boot)
    participant Router as AiQueryRouter
    participant Client as HttpModelAppClient
    participant ModelApp as FastAPI Model-app
    participant Ollama as Ollama LLM Service

    Farmer->>Core: POST /api/v1/ai/query {"query": "How to prevent onion rot in storage?"}
    Note over Core: Authenticates JWT & generates X-Correlation-ID
    Core->>Router: route(AiNaturalLanguageQueryRequest)
    Router->>Router: classify() -> GENERAL_ADVISORY (conf: 0.88)
    Router->>Client: processGeneralQuery(ModelAppQueryRequest)
    Client->>ModelApp: POST /api/v1/query [X-Correlation-ID]
    ModelApp->>Ollama: Generate agronomy advice
    Ollama-->>ModelApp: Advisory text
    ModelApp-->>Client: HTTP 200 ModelAppQueryResponse
    Client-->>Router: ModelAppQueryResponse
    Router-->>Core: AiQueryResponse (type: GENERAL_ADVISORY)
    Core-->>Farmer: HTTP 200 {"success": true, "data": {...}}
```

### 3.2 Factual Mandi Market Data Flow
```mermaid
sequenceDiagram
    autonumber
    actor Farmer as Android Farmer Client
    participant Core as Core Backend (Spring Boot)
    participant Router as AiQueryRouter
    participant Client as HttpModelAppClient
    participant ModelApp as FastAPI Model-app
    participant Gov as data.gov.in (AGMARKNET)

    Farmer->>Core: POST /api/v1/ai/query {"query": "What is today's onion price in Nagpur?"}
    Core->>Router: route()
    Router->>Router: classify() -> MARKET_DATA (conf: 0.90, market: Nagpur)
    Router->>Client: getMarketData("Onion", ["Nagpur"], null, 20)
    Client->>ModelApp: GET /api/v1/market-data?commodity=Onion&markets=Nagpur
    ModelApp->>Gov: Live REST API Query
    Gov-->>ModelApp: Mandi price records
    ModelApp-->>Client: HTTP 200 ModelAppMarketDataResponse
    Client-->>Router: ModelAppMarketDataResponse
    Router-->>Core: AiQueryResponse (type: MARKET_DATA, answer: "Current modal price...")
    Core-->>Farmer: HTTP 200 ApiResponse
```

### 3.3 Asynchronous Mandi Recommendation Job Flow
```mermaid
sequenceDiagram
    autonumber
    actor Client as Android / API Client
    participant Core as Core Backend
    participant ModelApp as FastAPI Model-app
    participant Redis as Redis Job Store
    participant RMQ as RabbitMQ Queue
    participant Worker as Background Worker

    Client->>Core: POST /api/v1/ai/recommend/async {crop: Onion, loc: [28.61, 77.20], qty: 10}
    Core->>ModelApp: POST /api/v1/recommend/async [X-Correlation-ID]
    ModelApp->>Redis: Set job:uuid -> status: QUEUED
    ModelApp->>RMQ: Publish message to ai.recommendations
    ModelApp-->>Core: HTTP 202 Accepted {job_id, poll_url}
    Core-->>Client: HTTP 202 Accepted {job_id, poll_url}

    par Background Consumer
        RMQ->>Worker: Consume message
        Worker->>Redis: Set job:uuid -> status: PROCESSING
        Worker->>Worker: Run MandiRecommender economics
        Worker->>Redis: Set job:uuid -> status: COMPLETED, result: {...}
        Worker->>RMQ: BasicAck
    end

    loop Client Polling
        Client->>Core: GET /api/v1/ai/jobs/{job_id}
        Core->>ModelApp: GET /api/v1/jobs/{job_id}
        ModelApp->>Redis: Read job state
        ModelApp-->>Core: HTTP 200 {status: COMPLETED, result: {...}}
        Core-->>Client: HTTP 200 {status: COMPLETED, result: {...}}
    end
```

---

## 4. Non-Functional Requirements & Design Principles

### 4.1 Fault Isolation & Circuit Protection
- **Decoupled Architecture**: If Model-app is offline or experiencing heavy load, Core Backend operational services (auth, profiles, lot listings, direct buyer offers) remain 100% operational.
- **Controlled Failure Translation**: External service failures (e.g. data.gov.in API timeouts, Ollama offline) are converted into structured, sanitized HTTP 502/503 domain exceptions without throwing unhandled 500 crashes.

### 4.2 Security & Least Privilege
- **Internal Microservice Isolation**: Model-app, Redis, RabbitMQ, and Ollama are deployed on an internal private network and are never directly addressable from public Android clients.
- **Zero Credential Leakage**: Database connection strings, RabbitMQ credentials, Redis authentication keys, and `DATA_GOV_API_KEY` are injected exclusively via environment variables and never surfaced in client responses.

### 4.3 Observability & Request Tracing
- **Correlation ID Tracking**: Every inbound request to Core Backend receives or preserves an `X-Correlation-ID` header, injected into SLF4J MDC, logged across Spring components, and transmitted over HTTP to Model-app, enabling distributed request tracing.
