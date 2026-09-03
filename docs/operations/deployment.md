# Deployment Topology & Operations Architecture

## 1. Multi-Tier Deployment Topology

MarketLink is structured into discrete, independently scalable service tiers:

```
                          ┌───────────────────────┐
                          │   Public Internet     │
                          └──────────┬────────────┘
                                     │ HTTPS (Port 443)
                                     ▼
                          ┌───────────────────────┐
                          │  Ingress / Reverse    │
                          │     Proxy (NGINX)     │
                          └──────────┬────────────┘
                                     │ HTTP (Port 8080)
                                     ▼
                    ┌───────────────────────────────────┐
                    │      Core Backend Cluster         │
                    │   (Spring Boot 3.3.3 / Java 21)   │
                    └────────┬─────────────────┬────────┘
                             │                 │
             Internal REST   │                 │ Database TCP
             (Port 8000)     ▼                 ▼
  ┌──────────────────────────────────┐  ┌───────────────────────┐
  │         Model-app ASGI           │  │   PostgreSQL + Mongo  │
  │     (FastAPI / Uvicorn)          │  │   Relational + Images │
  └───────┬──────────────────┬───────┘  └───────────────────────┘
          │                  │
          ▼                  ▼
┌──────────────────┐  ┌──────────────────────┐
│  Redis 7 Cluster │  │   RabbitMQ Cluster   │
│  (Port 6379)     │  │   (Port 5672)        │
└─────────┬────────┘  └──────────┬───────────┘
          │                      │
          │                      ▼
          │           ┌──────────────────────┐
          │           │ Model-app Background │
          │           │   Workers (Scale N)  │
          │           └──────────┬───────────┘
          │                      │
          └──────────────────────┘
```

---

## 2. Service Component Tiers

| Service Tier | Tech Stack | Ingress Access | Scaling Strategy |
| :--- | :--- | :--- | :--- |
| **Core Backend** | Spring Boot / Java 21 | Public (via Ingress) | Stateless horizontal scaling behind load balancer |
| **Model-app API** | FastAPI / Uvicorn | Private (Backend only)| Horizontal scaling behind internal load balancer |
| **Model-app Workers**| Python / Pika Consumer | Private (No HTTP) | Scale worker pods horizontally based on RabbitMQ queue depth |
| **Redis 7** | In-memory Data Store | Private (Model-app) | Primary/Replica with Redis Sentinel |
| **RabbitMQ** | AMQP Message Broker | Private (Model-app) | Clustered mirrored queues (Quorum Queues) |
| **PostgreSQL** | Relational Database | Private (Backend only)| Primary with read replicas |
| **MongoDB** | Document Store | Private (Backend only)| Replica set |
| **Ollama Runtime** | Local C++ / Go Daemon | Private (Model-app) | CPU/GPU-accelerated dedicated inference node |

---

## 3. Environment Tiers

### 3.1 Development (Local)
- Core Backend runs via `./mvnw spring-boot:run` on `localhost:8080`.
- Model-app runs via `uvicorn src.main:app` on `localhost:8000`.
- In-memory H2 database can be enabled for zero-dependency local verification.

### 3.2 Testing (CI/CD Automated)
- Core Backend executes 147 unit and MockMvc integration tests.
- Model-app executes 50 targeted integration and repository tests.
- No live external services required; mocks isolate HTTP, Redis, and AMQP.

### 3.3 Production
- Containers deployed within a private Kubernetes cluster or container service.
- Strict network policies: only Core Backend accepts traffic from public ingress.
- External data fetching uses persistent egress NAT with configured rate limits.
