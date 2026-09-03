# MarketLink Backend

**SIH Problem Statement 26132: Strengthening Market Linkages and Price Discovery for Farmers**

MarketLink is an agricultural marketplace connecting farmers directly with buyers to eliminate intermediaries and facilitate fair price discovery. The backend is responsible for identity management, secure lot lifecycle processing, optimized image handling, voice-assisted operations, and robust REST APIs that drive the native Android client application.

**Current Implementation Status:** Phase 1, Phase 2, Phase 3 (Audit), Phase 2A/2B (Model-app Integration), and the AI Query Routing Refactor are complete. The backend is fully integrated, stable, and verified with 147 passing tests.

---

## Problem Statement

Farmers often struggle to find fair prices for their produce due to a lack of direct market access and reliance on intermediaries. MarketLink solves this by bridging the gap between farmers and buyers.

- **Market-Linkage:** Farmers list their produce (Lots) directly to buyers.
- **Price Discovery:** Real-time and historical market price data helps farmers make informed decisions about when and where to sell.
- **Fair Play:** The system ensures secure transactions through explicit buyer offers and farmer acceptances.
- **Deterministic AI Advisory:** Intelligent routing dispatches natural-language farmer queries to AGMARKNET spot data, XGBoost price predictions, geospatial mandi recommendations, or Ollama agronomy advisory.

> **Important:** In MarketLink, markets are *not* intermediaries. The `Market` entity represents geographical market/location reference data used exclusively for market context and price discovery analysis. Farmers connect *directly* with buyers.

---

## Backend Responsibilities

**Included:**
- Authentication & Authorization (Stateless JJWT)
- Farmer & Buyer Profiles
- Crop & Market Master Data Management
- Produce Lot Lifecycle Management
- Optimized Multipart Image Processing & Persistence
- Location Domain Model (`@Embeddable Location` with bounds verification)
- AI Advisory & Deterministic Query Routing (`AiQueryClassifier`, `AiQueryRouter`)
- Model-App HTTP Integration (`ModelAppClient`, `HttpModelAppClient` via Spring 6 `RestClient`)
- Market Price Observation & AGMARKNET Data Querying
- Buyer Offers (Creation, Acceptance, Rejection, Cancellation)
- Voice-Channel Operations (Price queries, pending offers)
- OpenAPI Documentation (SpringDoc 2.6.0)

**Intentionally Excluded:**
- Direct ML model execution or training inside Spring (Spring acts as gateway/orchestrator; ML belongs in Model-app)
- Complex financial settlement & payment gateways
- FPO (Farmer Producer Organization) functionality
- Firebase Storage & Realtime DB (We use PostgreSQL and MongoDB exclusively)

---

## Technology Stack

| Technology | Purpose |
| --- | --- |
| **Java 21** | Backend language |
| **Spring Boot 3.3.3** | Application framework |
| **Spring Security** | Authentication/authorization framework |
| **JWT (JJWT 0.12.5)** | Backend authentication token standard |
| **Spring Data JPA** | PostgreSQL relational persistence |
| **PostgreSQL / H2** | Relational business database (H2 default for testing) |
| **Spring Data MongoDB** | MongoDB integration |
| **MongoDB** | Binary processed image storage |
| **Bean Validation** | Request input validation |
| **Lombok** | Boilerplate code reduction |
| **OpenAPI / Springdoc 2.6.0** | API documentation and Swagger UI |
| **Maven** | Build system |

---

## High-Level Architecture

```text
                    MarketLink Android
                           │
                           │ REST / JSON / Multipart
                           │
                           ▼
                 ┌─────────────────────┐
                 │   Spring Boot API   │
                 └──────────┬──────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
        Spring Security   Services    Controllers
              │             │
              │             │
              ▼             ▼
             JWT       Domain Logic
                            │
                    ┌───────┴────────┐
                    │                │
                    ▼                ▼
              PostgreSQL          MongoDB
              Business Data      Lot Images
```

---

## Package Architecture

The backend is structured into domain-driven packages inside `com.marketlink.backend`:

- `ai`: Quality Analysis abstraction.
- `auth`: Authentication controllers and services.
- `common`: Global exception handlers and shared DTOs (e.g. `ApiResponse`).
- `config`: OpenApi, CORS, and application-level configuration.
- `content`: FAQ and News content.
- `crop`: Crop master data domain.
- `domain`: Contains all core JPA and MongoDB entities (e.g. `user`, `crop`, `market`, `offer`, `image`).
- `image`: Image processing (`ImageProcessingService`), lot image lifecycle, and MongoDB integration.
- `lot`: Core produce listing and farmer lot lifecycle management.
- `market`: Market reference data domain.
- `marketplace`: Browsing and marketplace authorization policies.
- `marketprice`: Market price observations and discovery domain.
- `offer`: Buyer purchase offers and counter-negotiation logic.
- `profile`: Farmer and Buyer profile management.
- `security`: JWT filter, Principal, role-based authorization, and rate limiting.
- `verification`: Identity verification APIs.
- `voice`: Channel adapter for voice/IVR APIs (reuses existing domain services).

---

## Security Architecture

The backend uses a strict Spring Security + JWT architecture.

1. **Authentication:** The `JwtAuthenticationFilter` validates incoming JWTs. Upon success, it builds a `UserPrincipal` and sets it in the SecurityContext.
2. **Authorization:** Endpoints are protected via `@PreAuthorize`.
3. **Policies:** Specific policies like `@marketplaceAuth.isVerifiedFarmer(principal.id)` or `@marketplaceAuth.isLotOwner(principal.id, #lotId)` check verification state, active status, roles, and resource ownership before allowing execution.

> **Firebase Clarification:** Firebase Authentication is strictly an **Android-side** authentication mechanism. Firebase is *not* used as the backend database, image storage, or backend authentication provider in the current architecture. The backend validates only its own generated JWTs.

---

## Database Architecture

The application strictly separates operational business data from heavy binary assets:

- **PostgreSQL:** Stores all relational business data (Users, Farmer/Buyer Profiles, Crops, Markets, Lots, Offers, MarketPrices).
- **MongoDB:** Exclusively stores processed lot images.

### MongoDB Image Storage

**Why MongoDB?** Storing images in PostgreSQL leads to table bloat and performance degradation during normal relational queries. MongoDB's BSON `Binary` format allows fast read/write for image streaming without complex Base64 encoding overhead or filesystem dependency.

**Image Processing Pipeline:**
1. Multipart file upload (`LotImageController`).
2. Stream decoding and validation.
3. Resizing (preserves aspect ratio, maximum dimensions `1600x1600`).
4. Re-encoding to JPEG (`0.75` quality).
5. File size protection limit (`max 5MB`).
6. Saved directly as `org.bson.types.Binary` in MongoDB (`lot_images` collection).
7. Streamed directly to clients via `GET /api/v1/lots/{lotId}/images/{imageId}` with `Content-Type: image/jpeg`.

---

## Domain Model

- **Crop:** Master data (Name, Category, Unit). Uniqueness is case-insensitive.
- **Market:** Reference data (Name, District, State, Coordinates). 
- **Lot:** Farmer's produce listing (Quantity, Unit, Expected Price, Harvest Date, Status).
- **QualityAnalysisResult:** Model-agnostic wrapper for AI predictions (Score, Grade, Confidence, Provider).
- **Offer:** A buyer's proposal on a Lot (Offered Price, Quantity, Status).
- **MarketPrice:** Price observation for a specific crop/market. Used for discovery/analytics, *not* transactional processing.
- **LotImage:** MongoDB document containing the raw JPEG binary and metadata.

### Lot Lifecycle
`DRAFT` → `QUALITY_PENDING` → `QUALITY_VERIFIED` → `PUBLISHED` → `OFFER_RECEIVED` → `ACCEPTED` → `CLOSED`
*(Lifecycle state transitions are server-controlled to prevent unauthorized client mutations).*

---

## Voice Channel

The `voice` package is an interface channel adapter designed for IVR/Feature phone interactions. 
**It is not a separate business domain.** 
It leverages existing services (e.g. `MarketPriceService`, `OfferService`) to provide simplified endpoints like:
- `/api/v1/voice/prices`: Text-to-speech synthesized price summaries.
- `/api/v1/voice/offers`: Pending offers formatted for voice playback.
- `/api/v1/voice/offers/{id}/accept`: DTMF/voice-based safe offer acceptance.

---

## API Documentation

- **OpenAPI 3 / Swagger UI:** The backend API contract is fully documented. 
- Swagger UI can be accessed at `/swagger-ui/index.html` (or `/swagger-ui.html` depending on environment).
- API Docs JSON: `/v3/api-docs`
- Use the **BearerAuth** scheme (Provide your JWT token as `Bearer <token>`).

---

## API Endpoint Reference

*Note: This is a subset of the critical Android-facing APIs.*

| Feature | Method | Endpoint | Auth Required | Description |
| --- | --- | --- | --- | --- |
| **Crops** | GET | `/api/v1/crops` | As configured | Get available crops |
| **Markets** | GET | `/api/v1/markets` | As configured | Get market reference data |
| **Lots** | POST | `/api/v1/lots` | Verified Farmer | Create a new DRAFT lot |
| **Lots** | GET | `/api/v1/lots` | As configured | Browse published lots |
| **Lots** | GET | `/api/v1/farmers/me/lots` | Verified Farmer | Get owned lots |
| **Lots** | POST | `/api/v1/lots/{id}/publish` | Lot Owner | Publish lot to marketplace |
| **Images** | POST | `/api/v1/lots/{lotId}/images` | Lot Owner | Upload & compress crop photo |
| **Images** | GET | `/api/v1/lots/{lotId}/images/{imageId}` | Authorized | Stream raw JPEG binary |
| **Offers** | POST | `/api/v1/lots/{lotId}/offers` | Verified Buyer | Place a purchase offer |
| **Offers** | GET | `/api/v1/lots/{lotId}/offers` | Lot Owner / Buyer | Get offers for a lot |
| **Offers** | POST | `/api/v1/offers/{id}/accept` | Lot Owner | Accept an offer safely |
| **Prices** | GET | `/api/v1/market-prices` | As configured | Query market price history |
| **Prices** | GET | `/api/v1/market-prices/latest`| As configured | Get latest crop price |
| **Voice** | GET | `/api/v1/voice/prices` | As configured | Voice-friendly price query |
| **Voice** | POST | `/api/v1/voice/offers/{id}/accept`| Lot Owner | Voice offer acceptance |

---

## Request/Response Architecture

**Flow:** `HTTP Request` → `Controller` → `DTO Validation` → `Service` → `Repository` → `Database`
Entities are **never** exposed directly from Controllers to prevent data leakage and over-posting. We strictly use Request and Response DTOs wrapped in a unified `ApiResponse<T>`.

### Error Handling
Centralized via `GlobalExceptionHandler` mapping to standard HTTP statuses:
- `400 Bad Request`: Validation failure, bad image format, invalid state transition.
- `401 Unauthorized`: Missing or invalid JWT.
- `403 Forbidden`: Insufficient role or cross-user access violation.
- `404 Not Found`: Resource does not exist.
- `409 Conflict`: Concurrency issue or duplicate operation.

---

## Local Development Setup

### Requirements
- **Java 21**
- **Maven** (use `./mvnw`)
- **PostgreSQL** (Optional for local dev, defaults to in-memory H2)
- **MongoDB** (Required for image storage tests/runtime)

### Database Setup
By default, the `application.yml` is configured to use an in-memory **H2 Database** for relational data to facilitate easy local testing without PostgreSQL setup. 

To use PostgreSQL, override the datasource URL in a profile or environment variables:
```yaml
spring.datasource.url=jdbc:postgresql://localhost:5432/marketlink
spring.datasource.username=YOUR_USERNAME
spring.datasource.password=YOUR_PASSWORD
```
**MongoDB Setup:**
MongoDB is expected to run locally on `localhost:27017` with database `marketlink`. 
Override using env vars: `MONGODB_HOST`, `MONGODB_PORT`, `MONGODB_DATABASE`.

---

## Running the Application

To run the full test suite:
```bash
./mvnw clean test
```
*Current test suite result: 147 tests run, 0 failures, 0 errors (100% pass rate in 11.63s).*

To run the application locally:
```bash
./mvnw spring-boot:run
```
The server will start on port `8080`.

---

## Security Considerations for Future Contributors

- **Stateless:** Ensure the backend remains stateless. Do not use HTTP Sessions.
- **Ownership:** Never bypass resource ownership validation. Always check if the user mutating a resource actually owns it (e.g. `@marketplaceAuth.isLotOwner`).
- **Data Leakage:** Never expose JPA entities directly in API responses.
- **Images:** Do not introduce Base64 image payloads in normal JSON responses. Always use the dedicated multipart/binary stream endpoints. Do not store images in PostgreSQL.
- **Secrets:** Do not commit JWT secrets, database credentials, or API keys to the repository.

---

## Future Roadmap

**Completed:**
- Phase 1 & 2: Core domain logic and integrations.
- Phase 3: Comprehensive API and architectural audit.
- Phase 2A & 2B: FastAPI Model-app integration, ModelAppClient, Location domain value object.
- AI Query Routing Refactor: Deterministic AiQueryClassifier & AiQueryRouter for multi-capability routing.

**Future:**
- Native Kotlin Android Application integration.
- AI/ML real-time quality analysis model integration.
- Payment gateway and settlement infrastructure.
- Extended FPO dashboard functionality.

---

## Architecture Principles

- **PostgreSQL** → Business & transactional data.
- **MongoDB** → Processed lot images.
- **Spring Security + JWT** → Backend authentication & authorization.
- **Firebase** → Strictly Android-side authentication.
- **REST** → Standard client/backend communication.
- **OpenAPI** → API contract definition.
- **Voice** → Channel adapter, not a database layer.
- **AI** → Model-agnostic backend integration.
