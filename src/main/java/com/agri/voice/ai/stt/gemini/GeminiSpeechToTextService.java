package com.agri.voice.ai.stt.gemini;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpResponse;
import java.net.http.WebSocketHandshakeException;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Locale;
import java.util.Objects;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.agri.voice.ai.stt.SpeechToTextService;
import com.agri.voice.ai.stt.SttSessionContext;
import com.agri.voice.ai.stt.Transcript;
import com.agri.voice.ai.stt.TranscriptListener;
import com.agri.voice.ai.stt.TranscriptType;
import com.agri.voice.ai.stt.audio.AudioNormalizationException;
import com.agri.voice.ai.stt.audio.Pcm16AudioNormalizer;
import com.agri.voice.ai.stt.audio.PcmChunkBuffer;
import com.agri.voice.voice.audio.AudioFrame;
import com.fasterxml.jackson.databind.ObjectMapper;

import jakarta.annotation.PreDestroy;

@Service
public class GeminiSpeechToTextService implements SpeechToTextService {

    private static final Logger log = LoggerFactory.getLogger(GeminiSpeechToTextService.class);
    private static final int MAX_INPUT_FRAME_BYTES = 100_000;
    private static final long FINAL_TRANSCRIPTION_GRACE_MILLIS = 2_000;
    private static final int MAX_DIAGNOSTIC_CHARACTERS = 1_024;
    private static final Pattern NAMED_SECRET = Pattern.compile(
            "(?i)((?:authorization|x-goog-api-key|api[_-]?key|key|access[_-]?token|token)"
                    + "[\\\"']?\\s*[:=]\\s*[\\\"']?(?:bearer\\s+)?)[^\\s,;&\\\"']+");
    private static final Pattern URL_SECRET = Pattern.compile(
            "(?i)([?&](?:key|api[_-]?key|access[_-]?token|token)=)[^&\\s\\\"']+");
    private static final Pattern SENSITIVE_CONTENT = Pattern.compile(
            "(?i)[\\\"']?(?:transcript|audio|payload|media)[\\\"']?"
                    + "\\s*[:=]\\s*[\\\"']?[^,;&\\r\\n\\\"']+");
    private static final Pattern PHONE_NUMBER = Pattern.compile(
            "(?<![\\p{L}\\p{N}])\\+?\\d[\\d\\s().-]{7,}\\d(?![\\p{L}\\p{N}])");
    private static final Pattern LARGE_BASE64_VALUE = Pattern.compile(
            "(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{80,}={0,2}(?![A-Za-z0-9+/])");
    private static final Pattern CONTROL_CHARACTERS = Pattern.compile("[\\p{Cntrl}&&[^\\r\\n\\t]]");

    private final GeminiSttProperties properties;
    private final Pcm16AudioNormalizer normalizer;
    private final GeminiLiveTransportFactory transportFactory;
    private final GeminiResponseParser responseParser;
    private final GeminiProtocol protocol;
    private final Clock clock;
    private final ConcurrentMap<String, GeminiSession> sessions = new ConcurrentHashMap<>();

    @Autowired
    public GeminiSpeechToTextService(
            GeminiSttProperties properties,
            Pcm16AudioNormalizer normalizer,
            GeminiLiveTransportFactory transportFactory,
            GeminiResponseParser responseParser,
            ObjectMapper objectMapper) {
        this(properties, normalizer, transportFactory, responseParser, objectMapper, Clock.systemUTC());
    }

    GeminiSpeechToTextService(
            GeminiSttProperties properties,
            Pcm16AudioNormalizer normalizer,
            GeminiLiveTransportFactory transportFactory,
            GeminiResponseParser responseParser,
            ObjectMapper objectMapper,
            Clock clock) {
        this.properties = Objects.requireNonNull(properties);
        this.normalizer = Objects.requireNonNull(normalizer);
        this.transportFactory = Objects.requireNonNull(transportFactory);
        this.responseParser = Objects.requireNonNull(responseParser);
        this.protocol = new GeminiProtocol(Objects.requireNonNull(objectMapper));
        this.clock = Objects.requireNonNull(clock);
    }

    @Override
    public StartResult startSession(SttSessionContext context, TranscriptListener listener) {
        Objects.requireNonNull(context, "context must not be null");
        Objects.requireNonNull(listener, "listener must not be null");

        if (!properties.isEnabled()) {
            return StartResult.DISABLED;
        }
        if (!hasText(properties.getApiKey())) {
            return StartResult.MISSING_CREDENTIAL;
        }
        if (!validConfiguration()) {
            return StartResult.INVALID_CONFIGURATION;
        }

        GeminiSession[] created = new GeminiSession[1];
        try {
            sessions.compute(context.transportSessionId(), (key, existing) -> {
                if (existing != null) {
                    return existing;
                }
                created[0] = new GeminiSession(context, listener, transportFactory.create());
                return created[0];
            });
        } catch (RuntimeException exception) {
            return StartResult.REJECTED;
        }
        if (created[0] == null) {
            return StartResult.DUPLICATE;
        }

        created[0].start();
        log.atInfo()
                .addKeyValue("transportSessionId", context.transportSessionId())
                .addKeyValue("callSid", context.callSid())
                .addKeyValue("streamSid", context.streamSid())
                .addKeyValue("provider", "gemini")
                .log("Speech-to-text session starting");
        return StartResult.STARTING;
    }

    @Override
    public AudioResult acceptAudio(String transportSessionId, AudioFrame frame) {
        if (!hasText(transportSessionId) || frame == null) {
            return AudioResult.INVALID_AUDIO;
        }
        GeminiSession session = sessions.get(transportSessionId);
        if (session == null) {
            return AudioResult.NO_SESSION;
        }
        return session.accept(frame);
    }

    @Override
    public StopResult stopSession(String transportSessionId) {
        if (!hasText(transportSessionId)) {
            return StopResult.NOT_FOUND;
        }
        GeminiSession session = sessions.remove(transportSessionId);
        if (session == null) {
            return StopResult.NOT_FOUND;
        }
        session.requestStop();
        return StopResult.STOPPED;
    }

    @PreDestroy
    void shutdown() {
        sessions.forEach((id, session) -> session.requestStop());
        sessions.clear();
    }

    int activeSessionCount() {
        return sessions.size();
    }

    private boolean validConfiguration() {
        String mode = properties.getMode() == null
                ? ""
                : properties.getMode().trim().toUpperCase(Locale.ROOT);
        return properties.getSampleRate() == Pcm16AudioNormalizer.TARGET_SAMPLE_RATE
                && hasText(properties.getModel())
                && secureEndpoint(properties.getEndpoint())
                && ("VERBATIM".equals(mode) || "SMART".equals(mode))
                && properties.getQueueCapacity() > 0
                && properties.getQueueCapacity() <= 100
                && properties.getCustomVocabulary().size() <= 1_000
                && positive(properties.getConnectTimeout())
                && positive(properties.getSetupTimeout())
                && positive(properties.getSendTimeout());
    }

    private boolean positive(Duration duration) {
        return duration != null && !duration.isNegative() && !duration.isZero();
    }

    private boolean secureEndpoint(String endpoint) {
        if (!hasText(endpoint)) {
            return false;
        }
        try {
            URI uri = URI.create(endpoint);
            return "wss".equalsIgnoreCase(uri.getScheme()) && hasText(uri.getHost());
        } catch (IllegalArgumentException exception) {
            return false;
        }
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private URI authenticatedEndpoint() {
        String separator = properties.getEndpoint().contains("?") ? "&" : "?";
        String encodedKey = URLEncoder.encode(properties.getApiKey(), StandardCharsets.UTF_8);
        return URI.create(properties.getEndpoint() + separator + "key=" + encodedKey);
    }

    private final class GeminiSession {

        private final SttSessionContext context;
        private final TranscriptListener transcriptListener;
        private final GeminiLiveTransport transport;
        private final PcmChunkBuffer chunkBuffer = new PcmChunkBuffer();
        private final ArrayBlockingQueue<byte[]> audioQueue;
        private final CompletableFuture<Void> setupComplete = new CompletableFuture<>();
        private final CompletableFuture<Void> transcriptionGracePeriod = new CompletableFuture<>();
        private final AtomicBoolean stopRequested = new AtomicBoolean();
        private final AtomicBoolean failed = new AtomicBoolean();
        private final AtomicLong transcriptSequence = new AtomicLong();
        private final AtomicLong audioFramesReceived = new AtomicLong();
        private final AtomicLong inputPcmBytes = new AtomicLong();
        private final AtomicLong normalizedPcmBytes = new AtomicLong();
        private final AtomicLong chunksQueued = new AtomicLong();
        private final AtomicLong chunksSentToGemini = new AtomicLong();
        private final AtomicLong interimTranscriptionEvents = new AtomicLong();
        private final AtomicLong finalTranscriptionEvents = new AtomicLong();

        private GeminiSession(
                SttSessionContext context,
                TranscriptListener transcriptListener,
                GeminiLiveTransport transport) {
            this.context = context;
            this.transcriptListener = transcriptListener;
            this.transport = Objects.requireNonNull(transport);
            this.audioQueue = new ArrayBlockingQueue<>(properties.getQueueCapacity());
        }

        private void start() {
            Thread.ofVirtual()
                    .name("gemini-stt-" + context.transportSessionId())
                    .start(this::run);
        }

        private synchronized AudioResult accept(AudioFrame frame) {
            audioFramesReceived.incrementAndGet();
            inputPcmBytes.addAndGet(frame.byteLength());
            if (stopRequested.get() || failed.get()) {
                return AudioResult.SESSION_CLOSED;
            }
            if (!context.streamSid().equals(frame.streamSid())
                    || context.inputSampleRate() != frame.sampleRate()
                    || context.channels() != frame.channels()
                    || context.bitsPerSample() != frame.bitsPerSample()
                    || frame.byteLength() <= 0
                    || frame.byteLength() > MAX_INPUT_FRAME_BYTES) {
                return AudioResult.INVALID_AUDIO;
            }

            try {
                byte[] normalized = normalizer.normalize(frame);
                normalizedPcmBytes.addAndGet(normalized.length);
                boolean emitted = false;
                for (byte[] chunk : chunkBuffer.append(normalized)) {
                    emitted = true;
                    if (!audioQueue.offer(chunk)) {
                        logBackpressure();
                        return AudioResult.BACKPRESSURE;
                    }
                    chunksQueued.incrementAndGet();
                }
                return emitted ? AudioResult.ACCEPTED : AudioResult.BUFFERED;
            } catch (AudioNormalizationException exception) {
                return AudioResult.INVALID_AUDIO;
            }
        }

        private synchronized void requestStop() {
            if (!stopRequested.compareAndSet(false, true)) {
                return;
            }
            byte[] finalChunk = chunkBuffer.drain();
            if (finalChunk.length > 0) {
                if (audioQueue.offer(finalChunk)) {
                    chunksQueued.incrementAndGet();
                } else {
                    logBackpressure();
                }
            }
        }

        private void run() {
            boolean connected = false;
            try {
                transport.connect(authenticatedEndpoint(), new TransportListener())
                        .get(properties.getConnectTimeout().toMillis(), TimeUnit.MILLISECONDS);
                connected = true;
                send(protocol.setup(properties));
                setupComplete.get(properties.getSetupTimeout().toMillis(), TimeUnit.MILLISECONDS);

                log.atInfo()
                        .addKeyValue("transportSessionId", context.transportSessionId())
                        .addKeyValue("callSid", context.callSid())
                        .addKeyValue("streamSid", context.streamSid())
                        .addKeyValue("provider", "gemini")
                        .log("Speech-to-text session ready");

                while (!stopRequested.get() || !audioQueue.isEmpty()) {
                    byte[] chunk = audioQueue.poll(100, TimeUnit.MILLISECONDS);
                    if (chunk != null) {
                        send(protocol.audio(chunk));
                        chunksSentToGemini.incrementAndGet();
                    }
                }
                send(protocol.audioStreamEnd());

                // Allow Gemini time to return final transcription events before
                // the provider WebSocket is closed during session shutdown.
                try {
                    transcriptionGracePeriod.get(
                            FINAL_TRANSCRIPTION_GRACE_MILLIS,
                            TimeUnit.MILLISECONDS);
                } catch (TimeoutException ignored) {
                    log.atDebug()
                            .addKeyValue("transportSessionId", context.transportSessionId())
                            .addKeyValue("provider", "gemini")
                            .log("Timed out waiting for final transcription response");
                }
            } catch (TimeoutException exception) {
                fail("timeout", exception);
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
                fail("interrupted", exception);
            } catch (Exception exception) {
                fail("connection_or_send_failure", exception);
            } finally {
                if (connected) {
                    closeTransport();
                }
                audioQueue.clear();
                sessions.remove(context.transportSessionId(), this);
                log.atInfo()
                        .addKeyValue("transportSessionId", context.transportSessionId())
                        .addKeyValue("callSid", context.callSid())
                        .addKeyValue("streamSid", context.streamSid())
                        .addKeyValue("provider", "gemini")
                        .addKeyValue("failed", failed.get())
                        .addKeyValue("audioFramesReceived", audioFramesReceived.get())
                        .addKeyValue("inputPcmBytes", inputPcmBytes.get())
                        .addKeyValue("normalizedPcmBytes", normalizedPcmBytes.get())
                        .addKeyValue("chunksQueued", chunksQueued.get())
                        .addKeyValue("chunksSentToGemini", chunksSentToGemini.get())
                        .addKeyValue("interimTranscriptionEvents", interimTranscriptionEvents.get())
                        .addKeyValue("finalTranscriptionEvents", finalTranscriptionEvents.get())
                        .log("""
                            Speech-to-text session released
                            audioFramesReceived={}
                            inputPcmBytes={}
                            normalizedPcmBytes={}
                            chunksQueued={}
                            chunksSentToGemini={}
                            interimTranscriptionEvents={}
                            finalTranscriptionEvents={}
                            """,
                            audioFramesReceived.get(),
                            inputPcmBytes.get(),
                            normalizedPcmBytes.get(),
                            chunksQueued.get(),
                            chunksSentToGemini.get(),
                            interimTranscriptionEvents.get(),
                            finalTranscriptionEvents.get()
                        );
            }
        }

        private void send(String message) throws Exception {
            transport.sendText(message)
                    .get(properties.getSendTimeout().toMillis(), TimeUnit.MILLISECONDS);
        }

        private void closeTransport() {
            try {
                transport.close().get(properties.getSendTimeout().toMillis(), TimeUnit.MILLISECONDS);
            } catch (Exception exception) {
                failed.set(true);
            }
        }

        private void handleResponse(String message) {
            GeminiResponseParser.ParseResult parsed = responseParser.parse(message);
            if (!parsed.successful()) {
                log.atWarn()
                        .addKeyValue("transportSessionId", context.transportSessionId())
                        .addKeyValue("callSid", context.callSid())
                        .addKeyValue("streamSid", context.streamSid())
                        .addKeyValue("reason", "malformed_provider_message")
                        .log("Speech-to-text provider message ignored");
                return;
            }
            logProviderMessageShape(parsed);
            if (parsed.setupComplete()) {
                setupComplete.complete(null);
            }
            parsed.transcripts().forEach(parsedTranscript -> {
                if (parsedTranscript.type() == TranscriptType.INTERIM) {
                    interimTranscriptionEvents.incrementAndGet();
                } else if (parsedTranscript.type() == TranscriptType.FINAL) {
                    finalTranscriptionEvents.incrementAndGet();
                }
                Transcript transcript = new Transcript(
                        context.transportSessionId(),
                        context.callSid(),
                        context.streamSid(),
                        parsedTranscript.text(),
                        parsedTranscript.type(),
                        Instant.now(clock),
                        null,
                        transcriptSequence.getAndIncrement());
                try {
                    transcriptListener.onTranscript(transcript);
                } catch (RuntimeException exception) {
                    log.atWarn()
                            .addKeyValue("transportSessionId", context.transportSessionId())
                            .addKeyValue("callSid", context.callSid())
                            .addKeyValue("streamSid", context.streamSid())
                            .addKeyValue("reason", "transcript_listener_failure")
                            .log("Transcript listener rejected an event");
                }
                log.atInfo()
                        .addKeyValue("transportSessionId", context.transportSessionId())
                        .addKeyValue("callSid", context.callSid())
                        .addKeyValue("streamSid", context.streamSid())
                        .addKeyValue("transcriptType", transcript.type())
                        .addKeyValue("characterCount", transcript.text().length())
                        .addKeyValue("sequenceNumber", transcript.sequenceNumber())
                        .log("Voice transcript received");
            });
            if (!parsed.transcripts().isEmpty()) {
                transcriptionGracePeriod.complete(null);
            }
        }

        private void logProviderMessageShape(GeminiResponseParser.ParseResult parsed) {
            var event = parsed.providerError() == null ? log.atInfo() : log.atWarn();
            event.addKeyValue("transportSessionId", context.transportSessionId())
                    .addKeyValue("provider", "gemini")
                    .addKeyValue("topLevelFields", String.join(",", parsed.topLevelFields()))
                    .addKeyValue("serverContentFields", String.join(",", parsed.serverContentFields()))
                    .addKeyValue("setupComplete", parsed.setupComplete())
                    .addKeyValue("interimTranscriptCount", parsed.transcripts().stream()
                            .filter(transcript -> transcript.type() == TranscriptType.INTERIM)
                            .count())
                    .addKeyValue("finalTranscriptCount", parsed.transcripts().stream()
                            .filter(transcript -> transcript.type() == TranscriptType.FINAL)
                            .count());
            if (parsed.providerError() != null) {
                event.addKeyValue("providerErrorCode", parsed.providerError().code())
                        .addKeyValue("providerErrorStatus", safeDiagnostic(parsed.providerError().status()))
                        .addKeyValue("providerErrorMessage", safeDiagnostic(parsed.providerError().message()));
            }
            event.log(
                    "Gemini provider message received topLevelFields={} serverContentFields={} "
                            + "setupComplete={} interimTranscriptCount={} finalTranscriptCount={}",
                    String.join(",", parsed.topLevelFields()),
                    String.join(",", parsed.serverContentFields()),
                    parsed.setupComplete(),
                    parsed.transcripts().stream()
                            .filter(transcript -> transcript.type() == TranscriptType.INTERIM)
                            .count(),
                    parsed.transcripts().stream()
                            .filter(transcript -> transcript.type() == TranscriptType.FINAL)
                            .count());
        }

        private void fail(String reason, Throwable error) {
            fail(reason, error, null, null);
        }

        private void fail(String reason, int webSocketCloseCode, String webSocketCloseReason) {
            fail(reason, null, webSocketCloseCode, webSocketCloseReason);
        }

        private void fail(
                String reason,
                Throwable error,
                Integer webSocketCloseCode,
                String webSocketCloseReason) {
            if (!failed.compareAndSet(false, true)) {
                return;
            }
            stopRequested.set(true);
            setupComplete.completeExceptionally(new IllegalStateException("provider session failed"));
            audioQueue.clear();
            sessions.remove(context.transportSessionId(), this);
            FailureDiagnostics diagnostics = failureDiagnostics(
                    error,
                    webSocketCloseCode,
                    webSocketCloseReason);
            var event = log.atWarn()
                    .addKeyValue("transportSessionId", context.transportSessionId())
                    .addKeyValue("callSid", context.callSid())
                    .addKeyValue("streamSid", context.streamSid())
                    .addKeyValue("provider", "gemini")
                    .addKeyValue("reason", reason);
            if (diagnostics.exceptionClass() != null) {
                event.addKeyValue("exceptionClass", diagnostics.exceptionClass());
            }
            if (diagnostics.exceptionMessage() != null) {
                event.addKeyValue("exceptionMessage", diagnostics.exceptionMessage());
            }
            if (diagnostics.webSocketCloseCode() != null) {
                event.addKeyValue("webSocketCloseCode", diagnostics.webSocketCloseCode());
            }
            if (diagnostics.webSocketCloseReason() != null) {
                event.addKeyValue("webSocketCloseReason", diagnostics.webSocketCloseReason());
            }
            if (diagnostics.httpStatus() != null) {
                event.addKeyValue("httpStatus", diagnostics.httpStatus());
            }
            if (diagnostics.httpBody() != null) {
                event.addKeyValue("httpBody", diagnostics.httpBody());
            }
            event.log("Speech-to-text session failed {}", diagnostics.summary());
        }

        private void logBackpressure() {
            log.atWarn()
                    .addKeyValue("transportSessionId", context.transportSessionId())
                    .addKeyValue("callSid", context.callSid())
                    .addKeyValue("streamSid", context.streamSid())
                    .addKeyValue("reason", "audio_backpressure")
                    .addKeyValue("queueCapacity", properties.getQueueCapacity())
                    .log("Speech-to-text audio chunk rejected");
        }

        private final class TransportListener implements GeminiLiveTransport.Listener {

            @Override
            public void onText(String message) {
                handleResponse(message);
            }

            @Override
            public void onClosed(int statusCode, String reason) {
                if (!stopRequested.get()) {
                    fail("provider_disconnect", statusCode, reason);
                }
            }

            @Override
            public void onError(Throwable error) {
                fail("provider_transport_error", error);
            }
        }
    }

    private FailureDiagnostics failureDiagnostics(
            Throwable error,
            Integer webSocketCloseCode,
            String webSocketCloseReason) {
        Throwable rootCause = null;
        WebSocketHandshakeException handshakeException = null;
        Throwable current = error;
        for (int depth = 0; current != null && depth < 16; depth++) {
            rootCause = current;
            if (current instanceof WebSocketHandshakeException handshake) {
                handshakeException = handshake;
            }
            Throwable cause = current.getCause();
            if (cause == current) {
                break;
            }
            current = cause;
        }

        Throwable diagnosticException = handshakeException != null ? handshakeException : rootCause;
        Integer httpStatus = null;
        String httpBody = null;
        if (handshakeException != null) {
            HttpResponse<?> response = handshakeException.getResponse();
            if (response != null) {
                httpStatus = response.statusCode();
                httpBody = safeHttpBody(response.body());
            }
        }

        return new FailureDiagnostics(
                diagnosticException == null ? null : diagnosticException.getClass().getName(),
                diagnosticException == null ? null : safeDiagnostic(diagnosticException.getMessage()),
                webSocketCloseCode,
                safeDiagnostic(webSocketCloseReason),
                httpStatus,
                httpBody);
    }

    private String safeHttpBody(Object body) {
        if (body instanceof CharSequence characters) {
            return safeDiagnostic(characters.toString());
        }
        if (body instanceof byte[] bytes) {
            return safeDiagnostic(new String(bytes, StandardCharsets.UTF_8));
        }
        return null;
    }

    private String safeDiagnostic(String value) {
        if (!hasText(value)) {
            return null;
        }
        String sanitized = value;
        if (hasText(properties.getApiKey())) {
            sanitized = sanitized.replace(properties.getApiKey(), "[REDACTED]");
        }
        sanitized = URL_SECRET.matcher(sanitized).replaceAll("$1[REDACTED]");
        sanitized = NAMED_SECRET.matcher(sanitized).replaceAll("[REDACTED_CREDENTIAL]");
        sanitized = SENSITIVE_CONTENT.matcher(sanitized).replaceAll("[REDACTED_CONTENT]");
        sanitized = PHONE_NUMBER.matcher(sanitized).replaceAll("[REDACTED_PHONE]");
        sanitized = LARGE_BASE64_VALUE.matcher(sanitized).replaceAll("[REDACTED_DATA]");
        sanitized = CONTROL_CHARACTERS.matcher(sanitized).replaceAll(" ");
        sanitized = sanitized.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ').trim();
        if (sanitized.length() > MAX_DIAGNOSTIC_CHARACTERS) {
            sanitized = sanitized.substring(0, MAX_DIAGNOSTIC_CHARACTERS) + "...[truncated]";
        }
        return sanitized.isEmpty() ? null : sanitized;
    }

    private record FailureDiagnostics(
            String exceptionClass,
            String exceptionMessage,
            Integer webSocketCloseCode,
            String webSocketCloseReason,
            Integer httpStatus,
            String httpBody) {

        private String summary() {
            StringBuilder summary = new StringBuilder();
            append(summary, "exceptionClass", exceptionClass);
            append(summary, "exceptionMessage", exceptionMessage);
            append(summary, "webSocketCloseCode", webSocketCloseCode);
            append(summary, "webSocketCloseReason", webSocketCloseReason);
            append(summary, "httpStatus", httpStatus);
            append(summary, "httpBody", httpBody);
            return summary.isEmpty() ? "diagnostic=unavailable" : summary.toString();
        }

        private static void append(StringBuilder summary, String name, Object value) {
            if (value == null) {
                return;
            }
            if (!summary.isEmpty()) {
                summary.append(' ');
            }
            summary.append(name).append('=');
            if (value instanceof String text) {
                summary.append('"').append(text.replace('"', '\'')).append('"');
            } else {
                summary.append(value);
            }
        }
    }
}
