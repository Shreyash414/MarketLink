# Phase 4 — Real-Time Speech-to-Text Integration

## 1. Status and boundary

Phase 4 adds a real-time Speech-to-Text boundary between the existing Exotel-compatible WebSocket media layer and Google's Gemini Live Transcription API.

Implemented flow:

```text
Voice WebSocket
  -> VoiceSession
  -> AudioFrame
  -> SpeechToTextService
  -> Pcm16AudioNormalizer
  -> bounded 100 ms chunk queue
  -> GeminiSpeechToTextService
  -> Gemini Live API WebSocket
  -> Transcript
```

The transcript stops at the STT boundary. Phase 4 does not contain an LLM, tool router, database query, TTS, outbound audio, real Exotel call, payment, or transaction implementation.

## 2. Official Gemini protocol used

The implementation follows Google's current Live Transcription WebSocket documentation:

- Model: `gemini-3.5-transcribe-live`
- Endpoint: `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`
- Server-to-server authentication: API key query parameter constructed only in memory
- First client message: `setup`
- Model resource name: `models/gemini-3.5-transcribe-live`
- Generation response modality: `TEXT`
- Input audio transcription configuration: language codes, custom vocabulary, and mode
- Audio message: `realtimeInput.audio`
- Audio MIME type: `audio/pcm;rate=16000`
- End signal: `realtimeInput.audioStreamEnd=true`
- Interim transcript: `serverContent.interimInputTranscription.text`
- Final transcript: `serverContent.inputTranscription.text`

References:

- <https://ai.google.dev/gemini-api/docs/live-api/live-transcribe>
- <https://ai.google.dev/gemini-api/docs/live-api/get-started-websocket>
- <https://ai.google.dev/gemini-api/docs/live-api/capabilities>

No request or response field was added based on guesswork. The adapter waits for the standard `setupComplete` server message before sending queued audio.

## 3. Provider-neutral STT domain

### `SpeechToTextService`

The application depends on this interface rather than on Gemini-specific code. It defines:

```text
startSession(context, listener)
acceptAudio(transportSessionId, frame)
stopSession(transportSessionId)
```

Operations return explicit status enums. Expected failure states therefore do not need to throw through the Exotel WebSocket callback.

Start results include:

- `STARTING`
- `DUPLICATE`
- `DISABLED`
- `MISSING_CREDENTIAL`
- `INVALID_CONFIGURATION`
- `REJECTED`

Audio results include:

- `ACCEPTED`
- `BUFFERED`
- `BACKPRESSURE`
- `NO_SESSION`
- `SESSION_CLOSED`
- `INVALID_AUDIO`

Stop is idempotent through `STOPPED` or `NOT_FOUND`.

Future `SarvamSpeechToTextService` or `OpenAISpeechToTextService` implementations can implement the same interface without changing `VoiceSession`.

### `SttSessionContext`

Contains only correlation and audio-format information:

- transport session ID
- `callSid`
- `streamSid`
- input sample rate
- channels
- bits per sample

It deliberately excludes caller and destination phone numbers.

### `Transcript`

Contains:

- transport session ID
- `callSid`
- `streamSid`
- transcript text
- `INTERIM` or `FINAL` type
- receipt timestamp
- detected language when officially available
- monotonic per-session sequence number

Transcript objects are delivered immediately to `TranscriptListener`. They are not persisted, accumulated in `VoiceSession`, returned to Exotel, or passed to an LLM.

The current documented Gemini live response does not define a detected-language field, so `detectedLanguage` remains empty instead of inventing a provider field.

## 4. Voice lifecycle integration

`VoiceWebSocketHandler` retains its Phase 2 event contract.

### Start

After a valid, first `start` event changes `VoiceSession` to `STARTED`, the handler creates an `SttSessionContext` and requests an STT session. Duplicate or conflicting Exotel starts do not create another STT session.

Missing Gemini credentials do not reject or close the Exotel-compatible WebSocket. The voice transport can continue operating and reports the STT result internally.

### Media

The existing `AudioFrameDecoder` still validates and base64-decodes the Exotel media payload. Only a frame successfully recorded by `VoiceSession` is offered to STT.

STT validates that:

- a corresponding STT association exists
- the session is still open
- `streamSid` matches
- the frame format matches the start event
- channels equal one
- bits per sample equal 16
- the frame is non-empty
- the frame stays under the existing 100,000-byte limit
- the sample rate is supported

### Stop and failures

The STT association is stopped for:

- Exotel `stop`
- WebSocket close
- WebSocket transport error
- Gemini disconnect
- Gemini transport error
- connection, setup, or send timeout
- application shutdown

Voice-session and STT-session maps are independent. A Gemini failure removes only the affected STT session and cannot close the Spring Boot application or another voice session.

No automatic reconnection is performed because replaying buffered or already-delivered audio could duplicate transcripts.

## 5. Audio normalization

Gemini receives raw signed PCM16, mono, little-endian audio at 16 kHz.

### 16 kHz input

Samples pass through unchanged. The byte array is already defensively copied by `AudioFrame` and normalization does not retain it.

### 8 kHz input

Samples are linearly interpolated to 16 kHz. The output contains approximately twice as many samples.

### 24 kHz input

Samples are linearly interpolated down to 16 kHz. The output contains approximately two-thirds as many samples.

### Invalid formats

The normalizer rejects:

- null frames
- empty audio
- odd byte counts that do not form complete PCM16 samples
- non-mono audio
- non-16-bit audio
- unsupported sample rates

The implementation uses a small internal linear interpolator and adds no large audio library. This is appropriate for the current prototype. The `Pcm16AudioNormalizer` boundary allows a measured production-quality resampler to replace it later without changing Gemini or voice-session code.

## 6. Chunking and backpressure

At 16 kHz, mono PCM16:

```text
16,000 samples/second × 2 bytes/sample × 0.1 second = 3,200 bytes
```

`PcmChunkBuffer` emits 3,200-byte chunks. It retains at most one partial chunk smaller than 3,200 bytes. The final partial chunk is sent before the stream-end signal.

Each Gemini session uses a bounded `ArrayBlockingQueue`. The default capacity is 20 chunks, or approximately two seconds of audio.

The inbound WebSocket thread uses non-blocking `offer`. It never waits for Gemini network I/O. If Gemini is too slow and the queue is full:

- the extra chunk is rejected
- `BACKPRESSURE` is returned
- a metadata-only warning is logged
- no unbounded memory growth occurs

A dedicated Java 21 virtual thread handles each Gemini transport session. Connection, setup, and send operations are bounded by timeouts.

## 7. Gemini transport isolation

`GeminiLiveTransport` abstracts provider WebSocket I/O. The production implementation uses Java's built-in `java.net.http.HttpClient` and `WebSocket` APIs, so no Gemini SDK or WebSocket library dependency was added.

The JDK transport:

- accepts an already-authenticated URI from the Gemini service
- handles fragmented text messages
- bounds inbound provider responses to 64,000 characters
- rejects unexpected binary messages
- exposes only message, close, and error callbacks
- performs a normal WebSocket close

The API key exists only inside `GeminiSttProperties` and the in-memory connection URI. The URI and exception messages are never logged.

## 8. Response parsing

`GeminiResponseParser` parses only the fields Phase 4 needs:

- setup completion
- interim input transcription text
- final input transcription text

Unknown valid message types are ignored. Blank or malformed JSON returns an explicit unsuccessful parse result. Complete provider payloads are not stored or logged.

Both interim and final results become internal `Transcript` objects with a monotonic sequence number and server receipt timestamp.

## 9. Language behavior

Automatic language identification is enabled by sending an empty `languageCodes` list. Gemini's documented behavior supports multilingual speech and code-switching, including Hindi and Indian English.

The property can optionally contain BCP-47 hints, but Phase 4 leaves it empty by default to support Hindi/Hinglish calls without premature language selection.

The default custom vocabulary is:

```text
wheat, rice, paddy, maize, गेहूं, धान, चावल, मंडी,
mandi, MSP, quintal, क्विंटल, किसान, FPO, फसल, भाव
```

The list is configured once through the environment rather than embedded in provider or business logic. Gemini documents a maximum of 1,000 terms; application validation enforces that maximum.

Transcription mode defaults to `VERBATIM`. `SMART` is also supported through configuration.

## 10. Configuration

`.env.example` contains names and safe defaults only:

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

Additional environment overrides defined by `application.yaml`:

```text
GEMINI_STT_ENDPOINT
GEMINI_STT_CONNECT_TIMEOUT
GEMINI_STT_SETUP_TIMEOUT
GEMINI_STT_SEND_TIMEOUT
```

Safe constraints:

- target rate must be 16,000
- mode must be `VERBATIM` or `SMART`
- queue capacity must be from 1 through 100
- vocabulary must not exceed 1,000 terms
- all timeouts must be positive
- model and endpoint must be nonblank
- provider endpoint must use `wss://` and contain a host

The application starts without an API key. A key is required only when a voice `start` event should open a real Gemini connection.

## 11. Security and privacy

The implementation does not log:

- `GEMINI_API_KEY`
- authenticated Gemini URI
- Authorization headers
- raw PCM bytes
- base64 audio
- full Gemini setup, audio, or response payloads
- transcript text
- caller or destination phone numbers

Metadata logging is limited to:

- transport session ID
- `callSid`
- `streamSid`
- provider name
- lifecycle result or generic failure reason
- transcript type
- transcript character count
- transcript sequence number
- bounded queue capacity when backpressure occurs

The key is not exposed through `/health`, `/media`, another endpoint, or an outbound message to the Exotel-compatible client.

Because a credential was supplied in conversation during development, it should be revoked and replaced with a newly generated key stored only in the local ignored `.env` file or a deployment secret manager.

## 12. Tests

Phase 4 adds tests for:

- 16 kHz pass-through
- 8 kHz to 16 kHz conversion
- 24 kHz to 16 kHz conversion
- empty, misaligned, stereo, and unsupported audio
- 100 ms chunk emission and bounded remainder
- final partial chunk drain
- official Gemini setup JSON
- official Gemini audio and stream-end JSON
- setup completion parsing
- interim transcript parsing
- final transcript parsing
- malformed Gemini responses
- configuration binding without a key
- missing key behavior
- disabled and invalid configuration behavior
- complete AudioFrame-to-fake-Gemini flow
- Gemini disconnect isolation
- duplicate start
- duplicate stop
- session cleanup
- multiple independent sessions
- bounded backpressure
- stream and format mismatch
- credential, audio, and transcript logging safety
- integration of voice start/media/stop with `SpeechToTextService`
- STT cleanup after abnormal voice socket close

The fake transport makes the automated suite deterministic and external-network independent. Test fixtures use synthetic PCM only.

## 13. Local tests

Complete suite:

```powershell
.\mvnw.cmd --no-transfer-progress clean verify
```

Local `/media` transport without waiting for Gemini:

```powershell
.\scripts\Test-MediaWebSocket.ps1
```

Real Gemini connection and silent-audio smoke test:

```powershell
.\scripts\Test-MediaWebSocket.ps1 `
  -StartDelayMilliseconds 2000 `
  -FrameCount 20 `
  -Realtime
```

The second command requires a current `GEMINI_API_KEY`. It streams generated silence, so it validates setup and audio transport but does not validate speech-recognition quality.

## 14. Known limitations

- Gemini Live Transcription documents a continuous-session limit of ten minutes.
- No session rotation or resumption exists.
- No reconnect is attempted after provider failure.
- Linear interpolation has not been benchmarked against a telephony-quality resampling library.
- No microphone or audio-file ingestion tool is committed.
- No real Exotel call is performed.
- No transcript persistence exists.
- No detected-language response metadata is parsed because the documented live response does not specify it.
- No client-side VAD is implemented; Gemini automatic VAD remains enabled.
- Transcripts are internal callbacks and are not sent back over `/media`.

## 15. Explicitly deferred to later phases

- LLM integration
- prompt management
- conversation state and intelligence
- controlled AI tool routing
- arbitrary or approved SQL execution
- market database entities and repositories
- `get_market_price`
- `get_price_history`
- `get_nearby_markets`
- TTS
- outbound audio framing
- real Exotel connectivity
- Exotel API calls
- authentication system
- payments and transactions

Phase 5 has not been started.

## 16. Latest manual verification result

The application was started on port 8080 with database/JPA auto-configuration disabled only for the verification process because the local Docker database engine was unavailable.

Verified successfully:

```text
Application startup: successful
GET /health: HTTP 200, {"status":"UP"}
ws://localhost:8080/media: connected
connected/start/20 real-time media frames/stop: accepted
voice-session cleanup: confirmed
application graceful shutdown: confirmed
```

The process environment contained a Gemini credential, so an external provider smoke test was attempted without printing or storing the value. The backend initiated the Gemini WebSocket session, but setup did not complete and the STT session failed cleanly without affecting `/media` or the application.

A separate metadata-only credential probe to Google's `v1beta/models` endpoint returned HTTP 400. The response body and credential were not printed. Therefore, real Gemini authentication, setup completion, and transcript generation are **not verified** with the supplied credential. A newly generated valid Gemini API key is required for the next manual smoke test.

The supplied credential should be revoked because it was exposed in conversation. It was not written to any repository file.

## 17. Final build result and file inventory

Required command:

```powershell
.\mvnw.cmd --no-transfer-progress clean verify
```

Final result:

```text
Tests run: 69
Failures: 0
Errors: 0
Skipped: 0
BUILD SUCCESS
```

Phase 4 created these application files:

```text
ai/stt/SpeechToTextService.java
ai/stt/SttSessionContext.java
ai/stt/Transcript.java
ai/stt/TranscriptListener.java
ai/stt/TranscriptType.java
ai/stt/NoOpSpeechToTextService.java
ai/stt/audio/AudioNormalizationException.java
ai/stt/audio/Pcm16AudioNormalizer.java
ai/stt/audio/PcmChunkBuffer.java
ai/stt/gemini/GeminiSttProperties.java
ai/stt/gemini/GeminiSttConfiguration.java
ai/stt/gemini/GeminiLiveTransport.java
ai/stt/gemini/GeminiLiveTransportFactory.java
ai/stt/gemini/JdkGeminiLiveTransport.java
ai/stt/gemini/JdkGeminiLiveTransportFactory.java
ai/stt/gemini/GeminiProtocol.java
ai/stt/gemini/GeminiResponseParser.java
ai/stt/gemini/GeminiSpeechToTextService.java
```

Phase 4 created seven test classes covering the audio, protocol, provider service, properties, and voice-to-STT boundary.

Modified files:

```text
VoiceWebSocketHandler.java
VoiceWebSocketIntegrationTest.java
application.yaml
.env.example
README.md
scripts/Test-MediaWebSocket.ps1
```

`PHASE_4_DOCUMENTATION.md` was added as the implementation record. `pom.xml` was not changed and no dependency was added.
