# Security Architecture & Threat Mitigation

## 1. Security Philosophy & Defense-in-Depth

MarketLink implements a defense-in-depth model protecting user identities, produce trade transactions, and internal computing infrastructure:

```
Layer 1: Edge Security & Ingress
  ├── HTTPS / TLS 1.3 Transport Encryption
  ├── CorrelationIdFilter (Audit Trail & Request Tracking)
  └── CORS Configuration (Restricted Origins)

Layer 2: Authentication & Authorization (Core Backend)
  ├── Stateless JJWT (0.12.5) Bearer Tokens
  ├── Role-Based Access Control (ROLE_FARMER, ROLE_BUYER, ROLE_ADMIN)
  └── Input Validation (Jakarta Bean Validation / Bounds Enforcement)

Layer 3: Private Microservice Isolation
  ├── Model-app deployed on private internal network (no public IP)
  ├── Core Backend acts as secure reverse proxy & gateway
  └── Redis and RabbitMQ bound to localhost / VPC only

Layer 4: Data & Secret Protection
  ├── Environment variable secret injection (.env ignored by Git)
  ├── Sanitized error responses (zero stack traces or paths leaked)
  └── Zero API keys shared with client mobile applications
```

---

## 2. Authentication & Authorization

### 2.1 JWT Issuance & Verification
- Farmers and buyers authenticate via `/api/v1/auth/login`.
- The Core Backend signs tokens using HMAC-SHA256 with `JWT_SECRET`.
- Tokens contain subject (user ID), phone number, role, issuance time, and expiration (default 24 hours).
- On each request, `JwtAuthenticationFilter` validates token integrity and sets the `Authentication` principal in Spring's `SecurityContextHolder`.

### 2.2 Role-Based Access Control (RBAC)
- **`ROLE_FARMER`**: Can create and publish produce lots, view bids, accept/reject buyer offers.
- **`ROLE_BUYER`**: Can search published lots, place bids, submit purchase offers.
- **Both Roles**: Can query the AI advisory, request price forecasts, and retrieve mandi recommendations.

---

## 3. Network Isolation & Service Protection

1. **Model-App Protection**: The Model-app runs on port `8000` bound to localhost / internal VPC. It does not possess public SSL certificates and denies direct public internet ingress.
2. **Database & Message Broker Isolation**: PostgreSQL, MongoDB, Redis, and RabbitMQ reject external connections and authenticate using environment credentials.

---

## 4. Auditability: Distributed Request Tracing

- Every inbound HTTP request is intercepted by `CorrelationIdFilter`.
- If the incoming request has an `X-Correlation-ID` header, it is validated and preserved; otherwise, a random UUID is generated.
- The ID is stored in a `ThreadLocal` context (`CorrelationIdContext`) and mapped to SLF4J MDC (`correlationId`).
- The `HttpModelAppClient` injects the correlation ID into outbound requests to Model-app.
- In the event of a security incident or runtime error, engineers can correlate client logs with Spring logs and Model-app worker logs across the entire distributed cluster.
