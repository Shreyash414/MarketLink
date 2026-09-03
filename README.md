# Agricultural AI Voice Assistant Backend

A Java 21 and Spring Boot modular monolith for an agricultural phone assistant. Phase 5 extends the verified Exotel-compatible audio and Gemini Live Transcription pipeline with provider-neutral conversation management and Gemini text generation.

## Current scope

- Spring Boot application targeting Java 21
- HTTP and future WebSocket support
- Validation support
- PostgreSQL development container and persistence dependencies
- `GET /health`
- `WS /media` for Exotel AgentStream-compatible events
- Protocol records for `connected`, `start`, `media`, `dtmf`, `stop`, `mark`, and `clear`
- Base64 PCM frame validation and metadata tracking
- Idempotent voice-session lifecycle and cleanup
- Future outbound PCM audio boundary with no implementation yet
- Unit, handler, logging-safety, and live WebSocket integration tests
- Reverse-proxy forwarded-header support
- Environment-configurable server port and WebSocket path
- Optional Cloudflare Quick Tunnel helper for `wss://<public-host>/media`
- Provider-neutral `SpeechToTextService` and transcript domain model
- Gemini Live Transcription WebSocket adapter using `gemini-3.5-transcribe-live`
- 8/16/24 kHz PCM normalization to 16 kHz mono PCM16
- 100 ms STT chunking with bounded, non-blocking backpressure
- Automatic language detection for Hindi, English, Hinglish, and supported code-switching
- Configurable transcription mode and agricultural vocabulary
- Provider-neutral `LLMService` request/response boundary
- Gemini Interactions API text adapter using `gemini-3.5-flash-lite`
- Per-call bounded conversation history with serialized turns
- Final-transcript-to-LLM routing with safe fallback responses

The backend is not connected to Exotel yet. Gemini STT and text generation are implemented, but assistant text is currently an internal callback/logged metadata event and is not converted to speech. Controlled tools, TTS, database entities, payments, and transactions are intentionally not implemented.

## Architecture boundary

The eventual request flow is:

```text
Farmer -> Exotel -> WebSocket -> Voice Session -> STT -> LLM
       -> Controlled Tool Router -> Backend Service -> PostgreSQL
       -> LLM -> TTS -> WebSocket -> Exotel -> Farmer
```

The LLM will never receive direct PostgreSQL access. Future LLM tool calls will be restricted to approved, read-only backend operations.

## Prerequisites

- Java 21
- Docker with Docker Compose
- Git
- `cloudflared` only when testing a public development WSS URL

Maven installation is not required because the Maven Wrapper is included.

## Local setup

1. Create your local environment file:

   PowerShell:

   ```powershell
   Copy-Item .env.example .env
   ```

   macOS/Linux:

   ```bash
   cp .env.example .env
   ```

2. Replace `DB_PASSWORD` in `.env` with a local-only password.

3. Start PostgreSQL:

   ```bash
   docker compose up -d
   ```

4. Run the application:

   PowerShell:

   ```powershell
   .\mvnw.cmd spring-boot:run
   ```

   macOS/Linux:

   ```bash
   ./mvnw spring-boot:run
   ```

5. Check liveness:

   ```bash
   curl http://localhost:8080/health
   ```

   Expected response:

   ```json
   {"status":"UP"}
   ```

## AgentStream WebSocket

The local endpoint is:

```text
ws://localhost:8080/media
```

The inbound protocol follows the official Exotel AgentStream event field names. A valid stream normally sends:

```text
connected -> start -> media... -> stop
```

`dtmf` and `mark` are also accepted. `clear` is modeled because it is an official outbound VoiceBot command; an inbound `clear` is recognized and safely ignored.

The `start` event must provide the call and stream identifiers, caller, destination, encoding, and a sample rate of `8000`, `16000`, or `24000`. Mono and signed 16-bit little-endian PCM are fixed by the AgentStream audio protocol. The implementation does not guess a missing sample rate.

Media payloads are base64-decoded into internal PCM frames. Only frame metadata and aggregate byte counts are retained; raw audio is not logged or accumulated in the voice session.

### Manual local WebSocket test

With the application running and a locally controlled PCM WAV file, execute:

```powershell
.\scripts\Test-MediaWebSocket.ps1 -WavPath '.\path\to\controlled-test.wav'
```

The script opens `/media` and sends a representative `connected`, `start`, `media`, and `stop` sequence using synthetic silent PCM. It does not contact Exotel.

The same lifecycle is exercised automatically against a real embedded WebSocket server with:

```powershell
.\mvnw.cmd -Dtest=VoiceWebSocketIntegrationTest test
```

## Phase 4: Gemini Live speech-to-text

The Phase 4 flow is:

```text
/media WebSocket
  -> VoiceSession
  -> validated AudioFrame
  -> SpeechToTextService
  -> PCM normalization and bounded 100 ms chunks
  -> GeminiSpeechToTextService
  -> Gemini Live API WebSocket
  -> interim/final Transcript callback
```

Gemini is never exposed as a public endpoint. Only this backend initiates the server-to-server connection. Phase 5 routes final transcripts to the LLM layer; no tool, database, or TTS step follows it yet.

The adapter follows the official [Gemini Live transcription protocol](https://ai.google.dev/gemini-api/docs/live-api/live-transcribe):

- Model: `gemini-3.5-transcribe-live`
- Output modality: `TEXT`
- Input: raw signed 16-bit, little-endian, mono PCM
- Gemini input rate: 16 kHz
- Transport: backend-to-Gemini secure WebSocket
- Interim field: `serverContent.interimInputTranscription`
- Final field: `serverContent.inputTranscription`
- Stream completion: `realtimeInput.audioStreamEnd`

### Gemini API key

A real STT connection requires `GEMINI_API_KEY`. Automated tests use a fake transport and never require or contact Gemini.

Copy `.env.example` to `.env`, then set the key only in the ignored local file:

```text
GEMINI_API_KEY=<your-current-key>
```

Never place the value in `application.yaml`, source code, scripts, command history, documentation, or Git. If the key is absent, `/health` and `/media` continue working; the STT start request returns `MISSING_CREDENTIAL` internally and no Gemini connection is attempted.

### Audio normalization and latency

- 16 kHz input is copied without resampling.
- 8 kHz input is linearly upsampled to 16 kHz.
- 24 kHz input is linearly downsampled to 16 kHz.
- Mono PCM16 little-endian format is preserved.
- Normalized bytes are grouped into 3,200-byte chunks, representing 100 ms at 16 kHz.
- Only one partial chunk smaller than 100 ms is retained per session.
- The default outbound queue holds at most 20 chunks, approximately two seconds of audio.
- Queue offers never block the inbound voice thread. When full, a frame is rejected with a metadata-only backpressure warning.
- No automatic reconnect is attempted, preventing accidental duplicate audio.

The lightweight linear resampler is appropriate for this prototype transport boundary. A production telephony-quality resampler can replace it behind the same normalization boundary if later quality measurements justify one.

### Language and vocabulary

`GEMINI_STT_LANGUAGE_CODES` is empty by default. Gemini therefore performs automatic language identification and can handle Hindi, Indian English, Hinglish, and code-switching.

The default agricultural vocabulary is configurable through `GEMINI_STT_CUSTOM_VOCABULARY` and includes terms such as `wheat`, `paddy`, `mandi`, `MSP`, `गेहूं`, `धान`, `क्विंटल`, `किसान`, `फसल`, and `भाव`.

`GEMINI_STT_MODE` defaults to `VERBATIM`. Set it to `SMART` if cleaned disfluencies and provider formatting are desired. Only `VERBATIM` and `SMART` are accepted.

### STT configuration

```text
GEMINI_API_KEY=
GEMINI_STT_ENABLED=true
GEMINI_STT_MODEL=gemini-3.5-transcribe-live
GEMINI_STT_SAMPLE_RATE=16000
GEMINI_STT_MODE=VERBATIM
GEMINI_STT_LANGUAGE_CODES=
GEMINI_STT_CUSTOM_VOCABULARY=wheat,rice,paddy,...
GEMINI_STT_QUEUE_CAPACITY=20
```

Connection, setup, and send timeouts have safe defaults in `application.yaml`. The target sample rate must remain `16000` for this implementation.
The provider endpoint must use `wss://`; an insecure `ws://` endpoint is rejected before a credential can be used.

### Session lifecycle

1. A valid Exotel-compatible `start` event creates the existing `VoiceSession`.
2. The handler asks `SpeechToTextService` to start a correlated STT session.
3. Gemini receives the official setup message and acknowledges setup.
4. Valid `media` frames are normalized, chunked, and queued without blocking the voice thread.
5. Interim and final Gemini responses become internal `Transcript` objects.
6. Only transcript type, character count, sequence, `callSid`, and `streamSid` are logged; transcript text is not logged.
7. `stop`, socket close, transport error, provider failure, or application shutdown releases the STT association and buffers.

Gemini currently limits continuous Live Transcription sessions to ten minutes. Session resumption or planned rotation is deferred until real call-duration requirements are known.

### Local Gemini connection smoke test

With PostgreSQL and the application running and a current key present in `.env`, send a locally controlled PCM WAV file in real-time:

```powershell
.\scripts\Test-MediaWebSocket.ps1 `
  -WavPath '.\path\to\controlled-test.wav' `
  -StartDelayMilliseconds 2000 `
  -Realtime
```

This validates `/media`, STT session setup, audio streaming, and clean completion. Use `-FinalWaitMilliseconds 22000` when also observing the real Phase 5 LLM response before the test sends `stop`. The script contains no credential and never prints the API key.

For a transcript-quality test, use a locally controlled 16 kHz mono PCM source or a future explicitly authorized Exotel call. Do not commit personal recordings.

### Phase 4 testing

Tests use an in-process fake Gemini transport, so builds remain deterministic and offline. They cover configuration binding, missing credentials, official JSON setup/audio/end messages, 8/16/24 kHz normalization, chunking, interim/final parsing, malformed responses, disconnects, duplicate stop/start, independent sessions, bounded backpressure, voice-handler integration, and secret/audio/transcript logging safety.

### Known Phase 4 limitations

- No real Exotel call or microphone capture exists yet.
- Transcript events are internal callbacks only; no transcript REST or WebSocket response is exposed.
- Detected-language metadata is left empty because the documented live transcript event contains transcript text but does not define a language-code response field.
- No retry or reconnection is attempted after a Gemini failure.
- No client-side VAD is implemented; Gemini server-side automatic VAD remains active.
- Live sessions are not rotated beyond Gemini's documented ten-minute limit.
- No transcript persistence exists.
- No tools, TTS, or outbound audio has been added.

## Phase 5: Conversation management and Gemini text generation

The current text-response flow is:

```text
Final Transcript
  -> ConversationManager
  -> provider-neutral LLMService
  -> GeminiLLMService
  -> Gemini Interactions API
  -> bounded AssistantResponse
```

Interim transcripts remain diagnostic events and do not call the LLM. A final transcript is accepted once by sequence number, added to the call's isolated conversation, and processed in order. Calls can run concurrently, but turns within one call are serialized so assistant history cannot be reordered.

The adapter follows the current official [Gemini Interactions API](https://ai.google.dev/api/interactions-api):

- Endpoint: `POST https://generativelanguage.googleapis.com/v1beta/interactions`
- Authentication: `x-goog-api-key` request header
- Model: `gemini-3.5-flash-lite`
- State: `store=false`; bounded context is managed locally per voice session
- History steps: `user_input` and `model_output`
- Response text: `steps[].content[]` from `model_output` steps
- Default generation budget: 96 output tokens with `minimal` thinking
- Default request timeout: 20 seconds

No Gemini SDK dependency is needed. The implementation uses Java's built-in asynchronous HTTP client and limits both provider response bytes and accepted assistant text characters.

### LLM configuration

The shared `GEMINI_API_KEY` is used unless `GEMINI_LLM_API_KEY` is explicitly provided. Do not set the optional override unless STT and LLM intentionally use different keys.

```text
GEMINI_LLM_ENABLED=true
# GEMINI_LLM_API_KEY=optional_separate_key
GEMINI_LLM_MODEL=gemini-3.5-flash-lite
GEMINI_LLM_TIMEOUT=20s
GEMINI_LLM_MAX_OUTPUT_TOKENS=96
GEMINI_LLM_MAX_INPUT_CHARACTERS=16000
GEMINI_LLM_MAX_RESPONSE_CHARACTERS=2000
GEMINI_LLM_MAX_RESPONSE_BODY_BYTES=262144
GEMINI_LLM_THINKING_LEVEL=minimal
```

Conversation limits are separately configurable through `CONVERSATION_MAX_MESSAGES`, `CONVERSATION_MAX_CONTEXT_CHARACTERS`, `CONVERSATION_MAX_MESSAGE_CHARACTERS`, and `CONVERSATION_DUPLICATE_WINDOW_SIZE`.

The system instruction is stored at `src/main/resources/prompts/agricultural-assistant.txt`. It requests concise Hindi, Hinglish, or English answers and explicitly forbids inventing live market data while Phase 6 tools are absent.

### Failure and lifecycle behavior

Disabled/missing/invalid configuration, timeouts, network failures, authentication failures, rate limiting, provider 4xx/5xx responses, malformed/empty bodies, and oversized responses become typed `LLMResponse` failures. The farmer-facing path receives a generic fallback without provider details. No retry is performed in Phase 5.

Conversation memory is removed on normal stop, WebSocket close, transport error, rejected STT startup, and application shutdown. A late LLM completion after cleanup is discarded. Logs contain correlation IDs, status, latency, and character counts—not API keys, prompts, transcripts, assistant text, raw audio, phone numbers, headers, or provider bodies.

### Manual real Gemini text test

With a valid key in the ignored `.env` file:

```powershell
.\scripts\Test-GeminiLlm.ps1 -Prompt 'What is MSP?'
```

The script prints the assistant answer on success and only bounded, redacted provider diagnostics on failure. It never prints the key. Automated tests use fakes/local HTTP only and do not require external credentials.

## Public WSS for development

Cloudflare Quick Tunnel is the recommended Phase 3 development option. It requires no purchased domain, Cloudflare account, tunnel token, or committed credential. Cloudflare terminates public TLS/WSS and proxies the WebSocket upgrade to the application over local HTTP.

Quick Tunnel URLs are temporary, have no uptime guarantee, and change whenever the tunnel is restarted. Do not treat this setup as a production deployment.

### 1. Start the application

Prepare `.env` and PostgreSQL as described in **Local setup**, then start Spring Boot:

```powershell
.\mvnw.cmd spring-boot:run
```

Verify the local endpoints before opening a tunnel:

```powershell
Invoke-RestMethod http://localhost:8080/health
.\scripts\Test-MediaWebSocket.ps1
```

Expected results include `status = UP` and a successful local WebSocket sequence.

### 2. Install cloudflared

On Windows:

```powershell
winget install --id Cloudflare.cloudflared --exact
```

Open a new terminal after installation and confirm:

```powershell
cloudflared --version
```

Alternatively, download the current Windows executable from the official [Cloudflare Tunnel downloads page](https://developers.cloudflare.com/tunnel/downloads/). On macOS, use `brew install cloudflared`; Linux users should use Cloudflare's documented package repository or binary.

### 3. Start the public tunnel

Use the optional helper:

```powershell
.\scripts\Start-CloudflareQuickTunnel.ps1
```

Or run Cloudflare directly:

```powershell
cloudflared tunnel --url http://localhost:8080
```

Keep that terminal running. The command prints a random URL similar to:

```text
https://random-words.trycloudflare.com
```

The corresponding endpoints are:

```text
https://random-words.trycloudflare.com/health
wss://random-words.trycloudflare.com/media
```

Use `https://` for HTTP and `wss://` for WebSocket. Do not append a second port.

### 4. Test the public endpoints

Replace the example hostname with the exact hostname printed by `cloudflared`:

```powershell
Invoke-RestMethod https://random-words.trycloudflare.com/health
.\scripts\Test-MediaWebSocket.ps1 -Uri 'wss://random-words.trycloudflare.com/media'
```

The WebSocket test sends only synthetic silent PCM and a local test lifecycle. It does not call or authenticate to Exotel.

### 5. Future Exotel configuration

When AgentStream is explicitly enabled and a later phase authorizes a real integration, the VoiceBot Applet WebSocket URL will be the generated `wss://.../media` URL. Do not use `ws://localhost:8080/media`, an `https://` URL, or an expired Quick Tunnel hostname in Exotel.

No Exotel SID, API key, API token, Basic Authorization value, or real call is required in Phase 3.

### Configuration reference

The following settings remain environment-driven:

```text
SERVER_PORT=8080
SERVER_FORWARD_HEADERS_STRATEGY=native
VOICE_WS_PATH=/media
VOICE_WS_MAX_TEXT_MESSAGE_SIZE=150000
```

- `SERVER_PORT` is the local origin port used by Spring Boot and the tunnel.
- `SERVER_FORWARD_HEADERS_STRATEGY=native` lets embedded Tomcat honor standard proxy forwarding information from a trusted local reverse proxy.
- `VOICE_WS_PATH` defaults to `/media`. Keep this value for the Exotel contract unless both the client URL and deployment configuration are intentionally changed together.
- `VOICE_WS_MAX_TEXT_MESSAGE_SIZE` accommodates the documented maximum base64 media frame plus its JSON envelope.

The application does not generate or contain a localhost public URL. The public WSS hostname is supplied externally by the tunnel.

### Troubleshooting

- **`cloudflared` is not recognized:** open a new terminal after installation or place `cloudflared.exe` on `PATH`.
- **Tunnel shows `502 Bad Gateway`:** confirm Spring Boot is running, `/health` works locally, and the tunnel URL uses the same `SERVER_PORT`.
- **WebSocket returns `404`:** confirm the URL ends with the configured `VOICE_WS_PATH`, normally `/media`.
- **WebSocket returns `400`, `403`, or `426`:** use `wss://` in the WebSocket client, verify the client sends a WebSocket upgrade, and do not test the socket with a normal browser address-bar request.
- **TLS/certificate error:** connect to the exact `trycloudflare.com` hostname printed by the current tunnel. Do not use a stale hostname or attempt local HTTPS.
- **Tunnel cannot connect to Cloudflare:** check firewall, VPN, or corporate network rules for outbound Cloudflare Tunnel connectivity, including port `7844`.
- **Quick Tunnel refuses to start:** Cloudflare documents that Quick Tunnels are incompatible with an existing `.cloudflared/config.yml` or `config.yaml`; temporarily move that file outside the Cloudflare configuration directory.
- **Socket disconnects when the tunnel stops:** long-lived WebSocket connections are expected to close when `cloudflared` exits or restarts.
- **Local test works but public WSS fails:** test the public `/health` URL first, then keep both the application and tunnel terminals open while running the WSS client.
- **Logs appear to omit correlation values:** Phase 2 attaches `callSid` and `streamSid` as structured logging key-value fields. Ensure the production log encoder includes SLF4J key-value pairs.

For production, replace the Quick Tunnel with an explicitly secured, stable deployment and a controlled hostname. Do not expose a development Quick Tunnel as a permanent service.

## Tests and build

PowerShell:

```powershell
.\mvnw.cmd clean verify
```

macOS/Linux:

```bash
./mvnw clean verify
```

## Package layout

```text
com.agri.voice
|-- VoiceAssistantApplication
|-- common
|-- config
|-- voice
|   |-- dto
|   `-- audio
|-- ai
|-- market
|-- farmer
`-- security
```
