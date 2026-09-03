# Agricultural AI Voice Assistant Backend

## Consolidated implementation documentation: Phases 1–3

**Status:** Phase 3 complete  
**Last verified:** 3 September 2026  
**Base package:** `com.agri.voice`  
**Application:** `agri-voice-assistant`  
**Current public-integration state:** Development WSS connectivity verified; no Exotel account connection or real call attempted

## 1. Product objective

The project is the backend foundation for an agricultural AI phone assistant. The eventual product is intended to let a farmer call an Exotel number, speak Hindi or Hinglish, and hear a concise answer based on approved agricultural-market data.

The required eventual flow is:

```text
Farmer
  -> Exotel
  -> Secure bidirectional WebSocket
  -> Voice Session
  -> Speech-to-Text
  -> LLM
  -> Controlled Tool Router
  -> Backend Service
  -> PostgreSQL
  -> LLM
  -> Text-to-Speech
  -> Secure bidirectional WebSocket
  -> Exotel
  -> Farmer
```

The permanent trust boundary is:

```text
LLM -> approved, validated tool request -> backend service -> PostgreSQL
```

The LLM must never receive database credentials, open a database connection, execute arbitrary SQL, or access PostgreSQL directly. The first tool set will be read-only, but none of those tools has been implemented yet.

## 2. Architecture decisions

The application is a modular monolith:

- One Spring Boot process
- One Maven build
- One executable JAR
- One codebase with domain-oriented packages
- PostgreSQL as the planned persistence store
- A transport boundary around Exotel-compatible WebSocket events
- No microservices, Kubernetes, Kafka, RabbitMQ, Redis, payments, or transactions

Public TLS is not implemented inside Spring Boot for development. A Cloudflare Quick Tunnel terminates HTTPS/WSS and forwards the request to the local HTTP/WebSocket server:

```text
Public client or future Exotel
  -> wss://temporary-host.trycloudflare.com/media
  -> Cloudflare TLS termination and WebSocket proxy
  -> ws://localhost:8080/media
  -> VoiceWebSocketHandler
```

This keeps local development unchanged while proving that the existing `/media` contract works through a secure public reverse tunnel.

## 3. Technology baseline

- Java source and bytecode target: 21
- Spring Boot: 3.5.16
- Maven Wrapper: 3.3.4
- Maven distribution selected by the wrapper: 3.9.11
- Embedded server: Apache Tomcat
- Database driver: PostgreSQL JDBC
- Local database image: `postgres:17-alpine`
- Public development tunnel tested with `cloudflared` 2026.8.3
- Version control: Git repository initialized on branch `main`

Maven coordinates:

```text
groupId:    com.agri
artifactId: voice-assistant
version:    0.0.1-SNAPSHOT
packaging:  jar
```

Build artifact:

```text
target/voice-assistant-0.0.1-SNAPSHOT.jar
```

## 4. Dependencies

Application dependencies in `pom.xml`:

1. `spring-boot-starter-web`
   - REST endpoints, JSON support, Spring MVC, and embedded Tomcat
2. `spring-boot-starter-websocket`
   - Raw Spring WebSocket endpoint and handler support
3. `spring-boot-starter-validation`
   - Validation foundation for future validated requests and tool inputs
4. `spring-boot-starter-data-jpa`
   - Persistence foundation; no entities or repositories exist yet
5. `org.postgresql:postgresql` with runtime scope
   - PostgreSQL JDBC driver
6. `spring-boot-starter-test` with test scope
   - JUnit 5, Spring Test, MockMvc, assertions, and test utilities

No dependency was added in Phase 3. `cloudflared` is an optional machine-level development CLI, not a Maven or application dependency.

No Exotel, STT, LLM, TTS, messaging, payment, tunnel SDK, or cloud-provider library has been added.

## 5. Project structure

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
|-- PROJECT_DOCUMENTATION.md
|-- scripts/
|   |-- Start-CloudflareQuickTunnel.ps1
|   `-- Test-MediaWebSocket.ps1
`-- src/
    |-- main/
    |   |-- java/com/agri/voice/
    |   |   |-- VoiceAssistantApplication.java
    |   |   |-- ai/package-info.java
    |   |   |-- common/HealthController.java
    |   |   |-- config/package-info.java
    |   |   |-- farmer/package-info.java
    |   |   |-- market/package-info.java
    |   |   |-- security/package-info.java
    |   |   `-- voice/
    |   |       |-- ExotelEventParser.java
    |   |       |-- ExotelEventType.java
    |   |       |-- VoiceSession.java
    |   |       |-- VoiceWebSocketConfig.java
    |   |       |-- VoiceWebSocketHandler.java
    |   |       |-- package-info.java
    |   |       |-- audio/
    |   |       |   |-- AudioFrame.java
    |   |       |   |-- AudioFrameDecoder.java
    |   |       |   `-- OutboundAudioSender.java
    |   |       `-- dto/
    |   |           |-- ClearEvent.java
    |   |           |-- ConnectedEvent.java
    |   |           |-- DtmfEvent.java
    |   |           |-- ExotelEvent.java
    |   |           |-- MarkEvent.java
    |   |           |-- MediaEvent.java
    |   |           |-- StartEvent.java
    |   |           `-- StopEvent.java
    |   `-- resources/application.yaml
    `-- test/java/com/agri/voice/
        |-- common/HealthControllerTest.java
        `-- voice/
            |-- ExotelEventParserTest.java
            |-- ExotelTestMessages.java
            |-- VoiceSessionTest.java
            |-- VoiceWebSocketHandlerTest.java
            |-- VoiceWebSocketIntegrationTest.java
            `-- audio/AudioFrameDecoderTest.java
```

## 6. Package responsibilities

- `com.agri.voice`: Spring Boot entry point and component-scan root.
- `common`: Shared application behavior, currently the health endpoint.
- `voice`: WebSocket transport, Exotel event protocol, and per-connection voice-session lifecycle.
- `voice.dto`: JSON protocol records only; no business or provider logic.
- `voice.audio`: Validated PCM frame abstraction, decoder, and future outbound-audio boundary.
- `config`: Reserved for cross-cutting configuration.
- `ai`: Reserved for later STT, LLM orchestration, controlled tool routing, and TTS. It must not directly access PostgreSQL.
- `market`: Reserved for approved read-only market services, persistence, and future tools.
- `farmer`: Reserved for farmer domain behavior and persistence.
- `security`: Reserved for future request verification, access policy, and secret-handling configuration.

Empty functional packages contain `package-info.java` so the intended modular boundaries remain visible without premature implementation.

## 7. Phase 1: backend foundation

Phase 1 created the project from an empty folder and supplied the minimum application foundation.

### 7.1 Application entry point

`VoiceAssistantApplication` is the single `@SpringBootApplication` entry point. Its package position makes Spring scan all project packages below `com.agri.voice`.

### 7.2 Health endpoint

Request:

```http
GET /health
```

Response:

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{"status":"UP"}
```

This is process liveness only. It intentionally does not claim database or provider readiness.

### 7.3 PostgreSQL development foundation

`compose.yaml` defines one `postgres:17-alpine` service with:

- Database, user, password, and port supplied by environment variables
- Container port `5432`
- A `pg_isready` health check
- Named volume `postgres-data`

JPA is configured with `ddl-auto: validate`, so the application is not allowed to silently create or alter the schema. Open EntityManager in View is disabled.

No table, migration, entity, repository, seed data, or SQL execution endpoint exists yet.

### 7.4 Local secret handling

Spring optionally imports `.env` as a properties file. `.env.example` provides placeholder values, while `.gitignore` excludes real `.env` variants. Database credentials remain environment-driven.

## 8. Phase 2: Exotel AgentStream WebSocket layer

Phase 2 added the transport and protocol foundation without adding speech recognition, AI, synthesized speech, database behavior, or real Exotel connectivity.

### 8.1 Endpoint and connection lifecycle

The endpoint is:

```text
ws://localhost:8080/media
```

`VoiceWebSocketConfig` registers `VoiceWebSocketHandler`. Every accepted WebSocket connection creates one in-memory `VoiceSession`, keyed by the Spring transport-session identifier.

Cleanup happens on:

- A valid `stop` event
- WebSocket closure
- Transport error

The session is removed from the concurrent session map and closed. Duplicate callbacks after cleanup are ignored safely. This prevents abandoned connection state from accumulating.

### 8.2 Protocol events

`ExotelEventType` recognizes exactly:

- `connected`
- `start`
- `media`
- `dtmf`
- `stop`
- `mark`
- `clear`

`ExotelEventParser` first parses a JSON object, checks the top-level `event` string, maps only known event names, and deserializes into the matching record. It returns a typed success or one of these explicit errors:

- `MALFORMED_JSON`
- `INVALID_ENVELOPE`
- `MISSING_EVENT`
- `UNKNOWN_EVENT`
- `INVALID_EVENT`

Malformed or unsupported messages are rejected without throwing through the WebSocket callback and without closing the application.

### 8.3 Start validation and stored session data

A valid `start` event initializes the session with:

- `callSid`
- `streamSid`
- `accountSid` when supplied
- caller/from
- destination/to
- encoding
- sample rate
- channels
- bits per sample
- lifecycle timestamps

The implementation accepts documented raw/slin encoding labels and only these configured sample rates:

```text
8000
16000
24000
```

The media format is fixed to mono, signed 16-bit little-endian PCM as required by the AgentStream audio protocol. A missing or unsupported sample rate is rejected; the application does not guess it.

Repeated or out-of-order lifecycle events return explicit session results rather than corrupting session state. Session states are `OPEN`, `STARTED`, `STOPPED`, and `CLOSED`.

### 8.4 Media decoding

For each `media` event, `AudioFrameDecoder` checks:

- A started session exists
- The event has a media object and payload
- The event `streamSid` matches the active session
- The base64 text is syntactically valid
- Encoded and decoded size limits are respected
- Decoded data is non-empty and aligned to the expected PCM frame boundary
- Sequence, chunk, and timestamp values are valid non-negative numbers when present

A successful decode creates an immutable-style `AudioFrame` containing:

- A defensive copy of PCM16 little-endian bytes
- stream identifier
- sequence number
- chunk number
- media timestamp in milliseconds
- server receipt time
- encoding
- sample rate
- channel count
- bits per sample

The session stores only aggregate frame count, aggregate byte count, and the latest frame metadata. It does not accumulate audio bytes. Raw PCM and base64 audio are never logged.

No decoded frame is sent to STT in this phase.

### 8.5 DTMF, mark, clear, and stop

- `dtmf`: accepted only for a started, matching stream with a digit value; no business action is performed.
- `mark`: accepted only for a started, matching stream with a mark name; no playback implementation exists.
- `clear`: modeled because it is part of the official VoiceBot command set. If received inbound, it is recognized and safely ignored as an outbound-only operation.
- `stop`: checks stream correlation, records the stop reason and time, removes the session, closes its resources, and closes the socket normally. Duplicate or unexpected stops cannot leak a session or crash the server.

### 8.6 Future outbound boundary

`OutboundAudioSender` is an unimplemented interface for a future phase. It defines operations to send PCM, send a playback mark, and clear queued playback. No TTS audio, outbound frame serialization, or provider integration is present.

### 8.7 Structured, privacy-conscious logging

Logs use structured key-value fields such as:

- transport session ID
- `callSid`
- `streamSid`
- event outcome or rejection reason
- safe frame metadata such as byte count and sequence number

The handler does not log:

- raw PCM
- base64 media
- Authorization headers
- API keys or tokens
- caller/from or destination/to phone numbers
- event JSON bodies

## 9. Phase 3: public secure WebSocket preparation

Phase 3 preserved all Phase 1 and Phase 2 Java behavior and made the WebSocket registration and server behavior suitable for deployment behind a tunnel or reverse proxy.

### 9.1 Configuration changes

The following environment-driven settings now apply:

```text
SERVER_PORT=8080
SERVER_FORWARD_HEADERS_STRATEGY=native
VOICE_WS_PATH=/media
VOICE_WS_MAX_TEXT_MESSAGE_SIZE=150000
```

- `SERVER_PORT` selects the local Spring Boot origin port.
- `SERVER_FORWARD_HEADERS_STRATEGY=native` lets embedded Tomcat process standard proxy-forwarding headers.
- `VOICE_WS_PATH` controls WebSocket registration and defaults to the unchanged `/media` contract.
- `VOICE_WS_MAX_TEXT_MESSAGE_SIZE` protects the text-message boundary while allowing the documented media envelope size.

`VoiceWebSocketConfig` validates that the configured path is nonblank and begins with `/`. There is no localhost URL embedded in application code. The public hostname is an external deployment concern.

### 9.2 Cloudflare Quick Tunnel workflow

The development workflow uses:

```powershell
cloudflared tunnel --url http://localhost:8080
```

Cloudflare supplies a random `https://<host>.trycloudflare.com` origin. The public WebSocket equivalent is:

```text
wss://<host>.trycloudflare.com/media
```

No domain purchase, Cloudflare account, token, certificate file, or tunnel SDK is required for this development workflow. Quick Tunnel URLs are ephemeral, change after restart, and are not a production deployment.

### 9.3 Optional tunnel helper

`scripts/Start-CloudflareQuickTunnel.ps1`:

- Uses `http://localhost:8080` and `/media` by default
- Accepts an alternate local URL or WebSocket path as parameters
- Verifies that `cloudflared` is installed
- Warns about a local Cloudflare configuration file that can conflict with Quick Tunnels
- Starts the tunnel in the foreground
- Detects the generated public hostname
- Prints the corresponding public health and WSS endpoints
- Prints the exact public WebSocket test command
- Contains no credentials or tokens

### 9.4 Manual WebSocket client

`scripts/Test-MediaWebSocket.ps1` can test either local WS or public WSS. Its default target is local:

```powershell
.\scripts\Test-MediaWebSocket.ps1
```

An alternate public endpoint is passed explicitly:

```powershell
.\scripts\Test-MediaWebSocket.ps1 -Uri 'wss://<public-host>/media'
```

The script sends representative `connected`, `start`, `media`, and `stop` messages with synthetic silent PCM. It does not contain credentials, contact Exotel, or use real call audio.

### 9.5 Actual public verification

An actual Cloudflare Quick Tunnel was installed and run in the verification environment. The temporary generated hostname was:

```text
classic-cleanup-cbs-disturbed.trycloudflare.com
```

While that tunnel was active:

- `https://classic-cleanup-cbs-disturbed.trycloudflare.com/health` returned HTTP 200 and `{"status":"UP"}`.
- `wss://classic-cleanup-cbs-disturbed.trycloudflare.com/media` accepted the WebSocket connection.
- The manual client successfully sent `connected`, `start`, one valid synthetic `media` frame, and `stop`.
- Application logs confirmed the connection, start handling, stop handling, and voice-session release.
- No raw audio, base64 payload, credentials, or phone numbers appeared in the logs.

The tunnel was then stopped deliberately. The hostname is therefore expired and must not be used as a stable endpoint. A fresh tunnel command will generate the current URL for the next test.

### 9.6 What Phase 3 did not do

- No Exotel AgentStream account connection
- No Exotel credential configuration
- No actual call
- No stable hostname or production deployment
- No application-managed TLS certificate
- No new authentication system
- No change to the inbound Exotel event contract
- No STT, LLM, TTS, tools, entities, or business behavior

## 10. Configuration and local operation

### 10.1 Prepare environment

```powershell
Copy-Item .env.example .env
```

Replace the placeholder database password. Never commit `.env`.

### 10.2 Start PostgreSQL

```powershell
docker compose up -d
```

### 10.3 Build and test

```powershell
.\mvnw.cmd clean verify
```

### 10.4 Start Spring Boot

```powershell
.\mvnw.cmd spring-boot:run
```

### 10.5 Verify local HTTP and WebSocket

```powershell
Invoke-RestMethod http://localhost:8080/health
.\scripts\Test-MediaWebSocket.ps1
```

### 10.6 Start and test public WSS

```powershell
.\scripts\Start-CloudflareQuickTunnel.ps1
```

In a separate terminal, replace the hostname with the one printed by the running tunnel:

```powershell
Invoke-RestMethod https://<public-host>/health
.\scripts\Test-MediaWebSocket.ps1 -Uri 'wss://<public-host>/media'
```

Keep both Spring Boot and `cloudflared` running during the public test.

## 11. Automated test coverage

The complete suite currently contains 40 tests:

```text
HealthControllerTest                 1
AudioFrameDecoderTest                5
ExotelEventParserTest               11
VoiceSessionTest                     7
VoiceWebSocketHandlerTest           15
VoiceWebSocketIntegrationTest        1
                                      --
Total                                40
```

Coverage includes:

- `/health` status and response body
- All seven supported event types
- Malformed JSON
- Non-object envelopes
- Unknown and missing event values
- Invalid event payloads
- Missing start fields
- Unsupported encoding or sample rate
- Session creation, start, stop, close, and cleanup
- Duplicate and unexpected lifecycle events
- Valid media decoding
- Invalid base64, invalid size, invalid metadata, and stream mismatch
- Frame metadata and multiple-frame aggregation
- DTMF, mark, and inbound clear handling
- Transport-close and transport-error cleanup
- No credentials, phone numbers, raw audio, or base64 payload in captured logs
- A real embedded-server WebSocket lifecycle

Latest complete verification result:

```text
Tests run: 40
Failures: 0
Errors: 0
Skipped: 0
BUILD SUCCESS
```

## 12. Runtime verification evidence

The executable JAR was started on port 8080. Because the current machine's Docker engine was unavailable, database and JPA auto-configuration were disabled only in the verification process environment. No project file was changed for this workaround.

Verified locally:

```text
Application startup: successful
Embedded Tomcat port: 8080
GET /health: HTTP 200, {"status":"UP"}
ws://localhost:8080/media: connected successfully
connected/start/media/stop: handled successfully
session cleanup after stop: confirmed
graceful shutdown: confirmed
```

Verified publicly through the temporary tunnel:

```text
Public HTTPS /health: HTTP 200, {"status":"UP"}
Public WSS /media: connected successfully
connected/start/media/stop: handled successfully
session cleanup after stop: confirmed
TLS/WSS termination: handled by Cloudflare
```

The normal database-backed startup remains dependent on a reachable PostgreSQL instance with the configured schema. Database entities and migrations are intentionally not part of Phases 1–3.

## 13. Commands used for Phase 3 verification

The significant commands were:

```powershell
# Full build and all Phase 1/2 tests
.\mvnw.cmd --no-transfer-progress clean verify

# Check whether cloudflared was installed
winget list --id Cloudflare.cloudflared --exact

# Install the optional developer tunnel CLI
winget install --id Cloudflare.cloudflared --exact `
  --accept-package-agreements --accept-source-agreements --silent

# Start the application from the verified JAR
java -jar target\voice-assistant-0.0.1-SNAPSHOT.jar

# Local liveness and WebSocket verification
Invoke-WebRequest http://localhost:8080/health
.\scripts\Test-MediaWebSocket.ps1

# Start an anonymous development tunnel
cloudflared tunnel --url http://localhost:8080

# Public liveness and WebSocket verification
Invoke-WebRequest https://<generated-host>.trycloudflare.com/health
.\scripts\Test-MediaWebSocket.ps1 `
  -Uri 'wss://<generated-host>.trycloudflare.com/media'

# Final repository and secret-ignore checks
git status --short
git check-ignore -v .env .cloudflared/config.yml ngrok.yml
```

The database/JPA exclusion used for the runtime-only web transport verification was process-scoped. It is not part of application configuration or the committed run instructions.

## 14. Security verification

Implemented safeguards:

- No API key, token, password, Exotel credential, or Authorization header is hard-coded
- `.env` and environment-specific secret files are ignored
- Cloudflare and ngrok local credential/config artifacts are ignored
- The Quick Tunnel helper uses no token
- No request headers or full inbound JSON bodies are logged
- No raw audio or base64 audio is logged
- Caller and destination numbers are not logged
- Correlation uses call and stream identifiers where available
- Invalid input is rejected without server failure
- Base64 and frame sizes are bounded before retention
- Sessions are removed on stop, disconnect, and transport failure
- Audio is not accumulated in session memory
- No arbitrary SQL path exists
- No LLM-to-database path exists
- No write-capable AI tool exists
- No payments or transactions exist
- The public tunnel is explicitly documented as temporary development infrastructure

Before a real or production Exotel connection, the deployment will need an explicitly approved stable-hosting and connection-security design. Phase 3 does not claim that an anonymous Quick Tunnel is a production security boundary.

## 15. Current limitations and deferred work

The following are deliberately deferred until explicitly authorized:

- Real Exotel AgentStream enablement and calls
- Exotel-side VoiceBot Applet configuration
- Stable production public hostname and availability controls
- Exotel request or connection verification
- Production TLS/reverse-proxy deployment
- Hindi/Hinglish STT
- LLM client, prompts, and conversation orchestration
- Controlled tool registry and authorization
- TTS and outbound PCM serialization
- Audio resampling, buffering, interruption, and playback control
- `Farmer`, `Market`, `Crop`, and `MarketPrice` database entities
- Database migrations and seed data
- `get_market_price(crop, market, date)`
- `get_price_history(crop, market, days)`
- `get_nearby_markets(location, crop)`
- Authentication beyond the current transport-safe structure
- Payments and transactions

Docker Desktop's Linux engine was unavailable during the latest runtime check. The HTTP/WebSocket application was verified with database auto-configuration excluded only for that process. This limitation was not concealed or represented as a database integration test.

## 16. Official protocol and deployment references

- Exotel AgentStream developer guide: <https://developer.exotel.com/docs/agentstream/developer-guide>
- Exotel VoiceBot Applet: <https://developer.exotel.com/docs/agentstream/stream-voicebot-applet>
- Cloudflare Quick Tunnels: <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/>
- Cloudflare Tunnel setup: <https://developers.cloudflare.com/tunnel/setup/>
- Cloudflare Tunnel downloads: <https://developers.cloudflare.com/tunnel/downloads/>
- Spring Boot reverse-proxy forwarding: <https://docs.spring.io/spring-boot/how-to/webserver.html>

## 17. Phase acceptance status

### Phase 1

- Java 21 Spring Boot Maven foundation: complete
- Package structure: complete
- Environment-driven configuration: complete
- PostgreSQL Compose foundation: complete
- `/health`: complete and verified
- Initial test/build/runtime verification: complete

### Phase 2

- `/media` WebSocket: complete and verified
- Seven Exotel event types: complete
- Safe JSON parsing and lifecycle handling: complete
- PCM frame validation and metadata: complete
- Session cleanup: complete
- Outbound-audio interface only: complete
- Phase 2 test suite: complete

### Phase 3

- Proxy-aware environment configuration: complete
- Existing `/media` contract preserved: complete
- Local WS retained: complete and verified
- Public development WSS documentation and helper: complete
- Actual public WSS test: complete
- TLS termination through tunnel: complete
- Secret and logging checks: complete
- Real Exotel connection: correctly deferred

Phase 4 has not been started.
