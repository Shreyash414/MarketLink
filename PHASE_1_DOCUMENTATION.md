# Agricultural AI Voice Assistant Backend

## Phase 1 implementation documentation

**Project:** Agricultural AI Voice Assistant Backend  
**Phase:** 1 - Backend foundation  
**Status:** Complete  
**Implementation date:** 3 September 2026  
**Base package:** `com.agri.voice`

## 1. Purpose

This project is the backend foundation for an agricultural AI phone assistant. The eventual product will allow a farmer to call an Exotel number, speak in Hindi or Hinglish, and receive a concise spoken answer based on approved backend data and operations.

Phase 1 deliberately implements only the foundation needed for later development. It does not implement telephony, audio processing, AI providers, tool execution, or database models.

## 2. Required long-term architecture

The target request path is:

```text
Farmer
  -> Exotel
  -> Bidirectional WebSocket
  -> Voice Session
  -> Speech-to-Text
  -> LLM
  -> Controlled Tool Router
  -> Backend Service
  -> PostgreSQL
  -> LLM
  -> Text-to-Speech
  -> Bidirectional WebSocket
  -> Exotel
  -> Farmer
```

The most important trust boundary is:

```text
LLM -> approved tool request -> controlled backend code -> PostgreSQL
```

The LLM must never receive database credentials, open a database connection, submit arbitrary SQL, or access PostgreSQL directly. Future V1 tools must be explicitly registered and read-only.

## 3. Architecture style

The application was created as a modular monolith.

- One Spring Boot application
- One Maven build
- One deployable JAR
- Domain-oriented packages inside one codebase
- PostgreSQL as the planned persistence store
- No microservices
- No Kubernetes
- No Kafka or RabbitMQ
- No payments or transactions

This keeps local development and deployment simple while preserving clear boundaries for future voice, AI, market, farmer, configuration, and security capabilities.

## 4. Technology baseline

- Java language target: 21
- Spring Boot: 3.5.16
- Maven Wrapper: 3.3.4
- Maven distribution used by the wrapper: 3.9.11
- Embedded HTTP server: Apache Tomcat through Spring Boot
- PostgreSQL development image: `postgres:17-alpine`
- Version control: Git, initialized with `main` as the initial branch

The machine used for verification had JDK 24 installed. Maven compiled the project with `release 21`, and the resulting class files have major version 65, which is Java 21 bytecode.

## 5. Maven coordinates

```text
groupId:    com.agri
artifactId: voice-assistant
version:    0.0.1-SNAPSHOT
packaging:  jar
```

The executable build artifact is:

```text
target/voice-assistant-0.0.1-SNAPSHOT.jar
```

## 6. Dependencies added

### Runtime and application dependencies

1. `spring-boot-starter-web`
   - Spring MVC
   - REST controller support
   - JSON serialization
   - Embedded Tomcat

2. `spring-boot-starter-websocket`
   - WebSocket foundation for a later Exotel bidirectional audio phase
   - No WebSocket endpoint or audio protocol is implemented in Phase 1

3. `spring-boot-starter-validation`
   - Jakarta Bean Validation support for future request and tool input validation

4. `spring-boot-starter-data-jpa`
   - PostgreSQL persistence foundation for later domain entities and repositories
   - No entity or repository is implemented in Phase 1

5. `org.postgresql:postgresql`
   - PostgreSQL JDBC driver
   - Runtime scope

### Test dependency

6. `spring-boot-starter-test`
   - JUnit 5
   - Spring Test
   - MockMvc
   - JSON-path assertions and supporting test libraries

No Exotel, STT, LLM, TTS, messaging, payment, or provider-specific SDK dependencies were added.

## 7. Project structure

```text
.
|-- .env.example
|-- .gitignore
|-- .mvn/
|   `-- wrapper/
|       `-- maven-wrapper.properties
|-- compose.yaml
|-- mvnw
|-- mvnw.cmd
|-- pom.xml
|-- README.md
|-- PHASE_1_DOCUMENTATION.md
`-- src/
    |-- main/
    |   |-- java/com/agri/voice/
    |   |   |-- VoiceAssistantApplication.java
    |   |   |-- ai/
    |   |   |   `-- package-info.java
    |   |   |-- common/
    |   |   |   `-- HealthController.java
    |   |   |-- config/
    |   |   |   `-- package-info.java
    |   |   |-- farmer/
    |   |   |   `-- package-info.java
    |   |   |-- market/
    |   |   |   `-- package-info.java
    |   |   |-- security/
    |   |   |   `-- package-info.java
    |   |   `-- voice/
    |   |       `-- package-info.java
    |   `-- resources/
    |       `-- application.yaml
    `-- test/
        `-- java/com/agri/voice/common/
            `-- HealthControllerTest.java
```

## 8. Package responsibilities

### `com.agri.voice`

Contains `VoiceAssistantApplication`, the single Spring Boot entry point. Component scanning begins here and covers all child packages.

### `com.agri.voice.common`

Contains shared application behavior. Phase 1 places the liveness controller here.

### `com.agri.voice.config`

Reserved for application and infrastructure configuration classes.

### `com.agri.voice.voice`

Reserved for voice sessions, audio transport, Exotel WebSocket handling, and later audio lifecycle behavior.

### `com.agri.voice.ai`

Reserved for STT, LLM orchestration, controlled tool routing, and TTS abstractions. Direct database access must not be introduced in this package.

### `com.agri.voice.market`

Reserved for market data, approved read-only market services, repositories, and the future market tool implementations.

### `com.agri.voice.farmer`

Reserved for farmer-related domain behavior and persistence.

### `com.agri.voice.security`

Reserved for authentication, authorization, request verification, secret-handling configuration, and future Exotel connection security.

The currently empty functional packages contain `package-info.java` files so the intended structure is documented and retained in Git without adding premature implementation classes.

## 9. Application configuration

The application configuration is stored in `src/main/resources/application.yaml`.

Configured values:

- Application name: `agri-voice-assistant`
- Optional loading of a local `.env` file as properties
- Database URL from `DB_URL`
- Database username from `DB_USERNAME`
- Database password from `DB_PASSWORD`
- Hibernate schema behavior: `validate`
- Open EntityManager in View: disabled
- Server port from `SERVER_PORT`, defaulting to `8080`
- Graceful server shutdown enabled

The application does not contain a real username, password, API key, Exotel credential, or provider credential.

## 10. Environment variables

`.env.example` documents the local variables:

```text
DB_NAME
DB_USERNAME
DB_PASSWORD
DB_PORT
DB_URL
SERVER_PORT
```

The example password is a placeholder and must be replaced locally. Developers should copy `.env.example` to `.env` and keep the resulting file private.

The `.gitignore` rules exclude `.env` and all `.env.*` variants while explicitly allowing `.env.example` to remain version-controlled.

No Exotel, LLM, STT, or TTS environment variables were added because those integrations are outside Phase 1.

## 11. PostgreSQL development configuration

`compose.yaml` defines one PostgreSQL service with:

- Image: `postgres:17-alpine`
- Database, username, password, and host port supplied through environment variables
- Container port `5432`
- `pg_isready` health check
- Named volume `postgres-data`

No schema, table, migration, seed data, entity, repository, or arbitrary SQL interface was created.

The Compose file was validated successfully with:

```powershell
docker compose config --quiet
```

## 12. Health endpoint

### Request

```http
GET /health
```

### Successful response

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{"status":"UP"}
```

This endpoint is a basic process liveness check. It does not currently test PostgreSQL or any external integration. A separate readiness design can be added later when database and provider behavior exists.

## 13. Automated test

`HealthControllerTest` is a focused Spring MVC slice test using `@WebMvcTest` and `MockMvc`.

It verifies that:

- `GET /health` is mapped
- The response status is HTTP 200
- The response is JSON-compatible
- The JSON field `status` equals `UP`

Test result:

```text
Tests run: 1
Failures: 0
Errors: 0
Skipped: 0
```

## 14. Build verification

The complete Maven lifecycle was run with:

```powershell
.\mvnw.cmd clean verify
```

Final result:

```text
BUILD SUCCESS
Total tests: 1
Failures: 0
Errors: 0
Skipped: 0
```

The build produced an executable Spring Boot JAR. Compilation output confirmed `release 21`, and `javap` confirmed Java 21 bytecode:

```text
major version: 65
```

## 15. Runtime verification

The application was started on verification port `18080`. Spring Boot reported:

```text
Spring Boot 3.5.16
Tomcat started on port 18080
Started VoiceAssistantApplication
```

A real HTTP request returned:

```text
HTTP_STATUS=200
CONTENT_TYPE=application/json
BODY={"status":"UP"}
```

The application was then stopped through graceful shutdown.

### Runtime environment limitation

Docker and Docker Compose were installed, but the Docker Desktop Linux engine was not running. An attempt to start Docker Desktop did not make the engine available. Its Windows service was stopped and could not be started by the current non-elevated session.

The machine also had an unrelated local PostgreSQL process listening on port 5432. Its credentials and ownership were unknown, so it was not modified or probed with guessed credentials.

For the HTTP runtime check only, database and JPA auto-configuration were disabled using a process-scoped Spring Boot environment override. This did not change `application.yaml` or any repository file. Consequently:

- Web application startup was verified
- Embedded Tomcat startup was verified
- The live `/health` endpoint was verified
- Normal PostgreSQL-backed startup was not verified in that environment
- Compose syntax was verified independently

## 16. Commands used during implementation and verification

The meaningful commands were:

```powershell
# Workspace and toolchain inspection
Get-ChildItem -Force
rg --files -g "AGENTS.md"
java -version
mvn -version
git --version
docker --version
docker compose version

# Spring Boot 3.x artifact version inspection
Invoke-WebRequest https://repo.maven.apache.org/maven2/org/springframework/boot/spring-boot-starter-parent/maven-metadata.xml

# Maven Wrapper generation
mvn org.apache.maven.plugins:maven-wrapper-plugin:3.3.4:wrapper -Dtype=only-script -Dmaven=3.9.11

# Git initialization
git init -b main

# Complete build and tests
.\mvnw.cmd clean verify
.\mvnw.cmd --no-transfer-progress clean verify

# Compose validation and attempted database startup
docker compose config --quiet
docker compose up -d
docker info

# Application runtime verification
java -jar target\voice-assistant-0.0.1-SNAPSHOT.jar
Invoke-WebRequest http://localhost:18080/health

# Java target verification
javap -verbose target\classes\com\agri\voice\VoiceAssistantApplication.class

# Secret-file ignore verification
git check-ignore -v .env
```

The system Maven command was initially unavailable. Maven 3.9.11 was temporarily downloaded outside the project to generate the standard wrapper. All normal project builds then used `mvnw.cmd`.

## 17. Security decisions implemented

- No credentials are hard-coded in Java or application configuration
- Local secrets are loaded from environment variables
- `.env` is ignored by Git
- `.env.example` contains names and placeholders only
- No credentials are logged by application code
- No arbitrary SQL endpoint or execution path exists
- No LLM database connection exists
- No write-capable LLM tool exists
- No payment or transaction behavior exists
- No external integration dependency is present
- Hibernate schema auto-creation is disabled; configuration uses validation

## 18. Work intentionally not implemented

The following remain outside Phase 1:

- Exotel AgentStream integration
- Exotel VoiceBot Applet integration
- WebSocket endpoint configuration
- Bidirectional audio frame handling
- Voice session state machine
- Call lifecycle management
- Hindi or Hinglish speech recognition
- Speech-to-Text provider integration
- LLM client or prompt implementation
- Controlled tool registry or router
- Tool authorization and validation
- Text-to-Speech provider integration
- Audio encoding, buffering, resampling, or playback
- `Farmer`, `Market`, `Crop`, or `MarketPrice` entities
- Repositories or database services
- Database migrations
- Seed market data
- `get_market_price`
- `get_price_history`
- `get_nearby_markets`
- Authentication or Exotel request verification
- Payments or transactions
- Microservices
- Kubernetes
- Kafka or RabbitMQ

## 19. Local development instructions

### Prerequisites

- Java 21
- Docker Desktop or another Docker-compatible engine
- Git

Maven does not need to be installed globally.

### Setup

```powershell
Copy-Item .env.example .env
```

Replace the placeholder `DB_PASSWORD` value in `.env`.

Start PostgreSQL:

```powershell
docker compose up -d
```

Run the complete test suite:

```powershell
.\mvnw.cmd clean verify
```

Run the application:

```powershell
.\mvnw.cmd spring-boot:run
```

Verify the endpoint:

```powershell
Invoke-RestMethod http://localhost:8080/health
```

Stop PostgreSQL without deleting its named data volume:

```powershell
docker compose down
```

## 20. Phase 1 acceptance summary

- Spring Boot Maven project created from an empty folder: complete
- Java 21 configured: complete
- Required dependencies added: complete
- Modular package structure created: complete
- Basic environment-driven application configuration created: complete
- `GET /health` created: complete
- README created: complete
- `.gitignore` created: complete
- `.env.example` created: complete
- `/health` automated test created: complete
- Full Maven test suite passed: complete
- Executable JAR build passed: complete
- Application web startup verified: complete
- Live `/health` response verified: complete
- Compose file validated: complete
- PostgreSQL-backed application startup: pending a working Docker engine or known development PostgreSQL instance
- Phase 2 implementation: not started

## 21. Approval gate

Phase 1 is complete and no Phase 2 functionality has been added. Further work should begin only after explicit approval of the next phase and its scope.
