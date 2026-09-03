package com.agri.voice.ai.stt.gemini;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.net.URI;
import java.net.http.HttpResponse;
import java.net.http.WebSocketHandshakeException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.BooleanSupplier;
import java.util.stream.Collectors;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;

import com.agri.voice.ai.stt.SpeechToTextService.AudioResult;
import com.agri.voice.ai.stt.SpeechToTextService.StartResult;
import com.agri.voice.ai.stt.SpeechToTextService.StopResult;
import com.agri.voice.ai.stt.SttSessionContext;
import com.agri.voice.ai.stt.Transcript;
import com.agri.voice.ai.stt.TranscriptType;
import com.agri.voice.ai.stt.audio.Pcm16AudioNormalizer;
import com.agri.voice.ai.stt.audio.PcmChunkBuffer;
import com.agri.voice.voice.audio.AudioFrame;
import com.fasterxml.jackson.databind.ObjectMapper;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;

class GeminiSpeechToTextServiceTest {

    private static final Instant NOW = Instant.parse("2026-09-03T00:00:00Z");
    private final List<GeminiSpeechToTextService> services = new ArrayList<>();

    @AfterEach
    void tearDown() {
        services.forEach(GeminiSpeechToTextService::shutdown);
    }

    @Test
    void missingApiKeyDoesNotOpenAProviderSession() {
        GeminiSttProperties properties = properties();
        properties.setApiKey("");
        FakeTransportFactory factory = new FakeTransportFactory(false);
        GeminiSpeechToTextService service = service(properties, factory);

        assertThat(service.startSession(context("transport-1", "stream-1"), transcript -> { }))
                .isEqualTo(StartResult.MISSING_CREDENTIAL);
        assertThat(service.activeSessionCount()).isZero();
        assertThat(factory.transports).isEmpty();
    }

    @Test
    void disabledAndInvalidConfigurationsAreRejectedLocally() {
        GeminiSttProperties disabled = properties();
        disabled.setEnabled(false);
        assertThat(service(disabled, new FakeTransportFactory(false))
                .startSession(context("transport-1", "stream-1"), transcript -> { }))
                .isEqualTo(StartResult.DISABLED);

        GeminiSttProperties invalid = properties();
        invalid.setSampleRate(8_000);
        assertThat(service(invalid, new FakeTransportFactory(false))
                .startSession(context("transport-2", "stream-2"), transcript -> { }))
                .isEqualTo(StartResult.INVALID_CONFIGURATION);

        GeminiSttProperties insecure = properties();
        insecure.setEndpoint("ws://localhost/provider");
        assertThat(service(insecure, new FakeTransportFactory(false))
                .startSession(context("transport-3", "stream-3"), transcript -> { }))
                .isEqualTo(StartResult.INVALID_CONFIGURATION);
    }

    @Test
    void streamsNormalizedAudioAndSignalsStreamEnd() throws Exception {
        FakeTransportFactory factory = new FakeTransportFactory(false);
        GeminiSpeechToTextService service = service(properties(), factory);

        assertThat(service.startSession(context("transport-1", "stream-1", 8_000), transcript -> { }))
                .isEqualTo(StartResult.STARTING);
        FakeTransport transport = factory.awaitTransport(0);
        assertThat(service.acceptAudio("transport-1", frame("stream-1", 8_000, new byte[1_600])))
                .isEqualTo(AudioResult.ACCEPTED);
        assertThat(service.stopSession("transport-1")).isEqualTo(StopResult.STOPPED);

        assertThat(await(() -> transport.closed, 3_000)).isTrue();
        assertThat(transport.messages).anySatisfy(message -> {
            assertThat(message).contains("audio/pcm;rate=16000");
            assertThat(message).contains("realtimeInput");
        });
        assertThat(transport.messages).anyMatch(message -> message.contains("audioStreamEnd"));
        assertThat(transport.endpoint.getQuery()).contains("key=test-key");
    }

    @Test
    void sendsAudioOnlyAfterSetupCompleteAndLogsAggregatePipelineCounts() throws Exception {
        Logger logger = (Logger) LoggerFactory.getLogger(GeminiSpeechToTextService.class);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.list = new CopyOnWriteArrayList<>();
        appender.start();
        logger.addAppender(appender);
        try {
            FakeTransportFactory factory = new FakeTransportFactory(false, null, false);
            List<Transcript> transcripts = new CopyOnWriteArrayList<>();
            GeminiSpeechToTextService service = service(properties(), factory);
            service.startSession(context("transport-1", "stream-1", 8_000), transcripts::add);
            FakeTransport transport = factory.awaitTransport(0);
            assertThat(await(transport::setupWasSent, 1_000)).isTrue();

            assertThat(service.acceptAudio(
                    "transport-1",
                    frame("stream-1", 8_000, new byte[1_600])))
                    .isEqualTo(AudioResult.ACCEPTED);
            assertThat(service.acceptAudio(
                    "transport-1",
                    frame("stream-1", 8_000, new byte[1_600])))
                    .isEqualTo(AudioResult.ACCEPTED);
            assertThat(transport.audioMessageCount()).isZero();

            transport.completeSetup();
            assertThat(await(() -> transport.audioMessageCount() == 2, 1_000)).isTrue();
            assertThat(transport.audioMessages()).hasSize(2).allSatisfy(audioJson -> {
                try {
                    var audioMessage = new ObjectMapper().readTree(audioJson);
                    assertThat(audioMessage.at("/realtimeInput/audio/mimeType").asText())
                            .isEqualTo("audio/pcm;rate=16000");
                    byte[] sentPcm = Base64.getDecoder().decode(
                            audioMessage.at("/realtimeInput/audio/data").asText());
                    assertThat(sentPcm)
                            .hasSize(PcmChunkBuffer.DEFAULT_CHUNK_BYTES)
                            .containsOnly((byte) 0);
                } catch (Exception exception) {
                    throw new AssertionError("outbound audio must be valid realtime-input JSON", exception);
                }
            });

            transport.emit("""
                    {"serverContent":{"interimInputTranscription":{"text":"interim"}}}
                    """);
            transport.emit("""
                    {"serverContent":{"inputTranscription":{"text":"final"}}}
                    """);
            assertThat(await(() -> transcripts.size() == 2, 1_000)).isTrue();

            assertThat(service.stopSession("transport-1")).isEqualTo(StopResult.STOPPED);
            assertThat(await(() -> transport.closed, 2_000)).isTrue();
            assertThat(await(
                    () -> capturedLogs(appender).contains("audioFramesReceived=\"2\""),
                    1_000)).isTrue();

            assertThat(capturedLogs(appender))
                    .contains("audioFramesReceived=\"2\"")
                    .contains("inputPcmBytes=\"3200\"")
                    .contains("normalizedPcmBytes=\"6400\"")
                    .contains("chunksQueued=\"2\"")
                    .contains("chunksSentToGemini=\"2\"")
                    .contains("interimTranscriptionEvents=\"1\"")
                    .contains("finalTranscriptionEvents=\"1\"")
                    .doesNotContain("interim\"")
                    .doesNotContain("final\"");
            assertThat(transcripts).extracting(Transcript::type)
                    .containsExactly(TranscriptType.INTERIM, TranscriptType.FINAL);
        } finally {
            logger.detachAppender(appender);
            appender.stop();
        }
    }

    @Test
    void forwardsCompleteSignedPcm16SamplesWithoutDroppingHighBytes() throws Exception {
        FakeTransportFactory factory = new FakeTransportFactory(false, null, false);
        GeminiSpeechToTextService service = service(properties(), factory);
        service.startSession(context("transport-1", "stream-1", 16_000), transcript -> { });
        FakeTransport transport = factory.awaitTransport(0);
        assertThat(await(transport::setupWasSent, 1_000)).isTrue();

        byte[] pcm = new byte[PcmChunkBuffer.DEFAULT_CHUNK_BYTES];
        byte[] signedSamples = {
                0x00, (byte) 0x80,
                (byte) 0xff, 0x7f,
                0x34, 0x12,
                (byte) 0xcc, (byte) 0xed
        };
        for (int offset = 0; offset < pcm.length; offset += signedSamples.length) {
            System.arraycopy(signedSamples, 0, pcm, offset, signedSamples.length);
        }

        assertThat(service.acceptAudio("transport-1", frame("stream-1", 16_000, pcm)))
                .isEqualTo(AudioResult.ACCEPTED);
        transport.completeSetup();
        assertThat(await(() -> transport.audioMessageCount() == 1, 1_000)).isTrue();

        var audioMessage = new ObjectMapper().readTree(transport.audioMessages().getFirst());
        byte[] sentPcm = Base64.getDecoder().decode(
                audioMessage.at("/realtimeInput/audio/data").asText());
        assertThat(sentPcm).containsExactly(pcm);

        transport.emit("""
                {"serverContent":{"inputTranscription":{"text":"complete"}}}
                """);
        assertThat(service.stopSession("transport-1")).isEqualTo(StopResult.STOPPED);
        assertThat(await(() -> transport.closed, 2_000)).isTrue();
    }

    @Test
    void emitsInterimAndFinalTranscriptsWithoutRetainingProviderMessages() throws Exception {
        FakeTransportFactory factory = new FakeTransportFactory(false);
        List<Transcript> transcripts = new CopyOnWriteArrayList<>();
        GeminiSpeechToTextService service = service(properties(), factory);
        service.startSession(context("transport-1", "stream-1"), transcripts::add);
        FakeTransport transport = factory.awaitTransport(0);
        assertThat(await(transport::setupWasSent, 1_000)).isTrue();

        transport.emit("""
                {"serverContent":{"interimInputTranscription":{"text":"गेहूं"}}}
                """);
        transport.emit("""
                {"serverContent":{"inputTranscription":{"text":"गेहूं का भाव"}}}
                """);

        assertThat(await(() -> transcripts.size() == 2, 1_000)).isTrue();
        assertThat(transcripts).extracting(Transcript::type)
                .containsExactly(TranscriptType.INTERIM, TranscriptType.FINAL);
        assertThat(transcripts).extracting(Transcript::sequenceNumber).containsExactly(0L, 1L);
        assertThat(transcripts).allSatisfy(transcript -> {
            assertThat(transcript.callSid()).isEqualTo("call-1");
            assertThat(transcript.streamSid()).isEqualTo("stream-1");
            assertThat(transcript.receivedAt()).isEqualTo(NOW);
            assertThat(transcript.detectedLanguage()).isNull();
        });
    }

    @Test
    void malformedProviderMessageDoesNotBreakTheSession() throws Exception {
        FakeTransportFactory factory = new FakeTransportFactory(false);
        List<Transcript> transcripts = new CopyOnWriteArrayList<>();
        GeminiSpeechToTextService service = service(properties(), factory);
        service.startSession(context("transport-1", "stream-1"), transcripts::add);
        FakeTransport transport = factory.awaitTransport(0);
        assertThat(await(transport::setupWasSent, 1_000)).isTrue();

        transport.emit("{broken");

        assertThat(transcripts).isEmpty();
        assertThat(service.activeSessionCount()).isOne();
    }

    @Test
    void providerDisconnectReleasesOnlyItsOwnSession() throws Exception {
        FakeTransportFactory factory = new FakeTransportFactory(false);
        GeminiSpeechToTextService service = service(properties(), factory);
        service.startSession(context("transport-1", "stream-1"), transcript -> { });
        service.startSession(context("transport-2", "stream-2"), transcript -> { });
        FakeTransport first = factory.awaitTransport(0);
        factory.awaitTransport(1);

        first.disconnect();

        assertThat(await(() -> service.activeSessionCount() == 1, 1_000)).isTrue();
        assertThat(service.acceptAudio("transport-2", frame("stream-2", 16_000, new byte[320])))
                .isEqualTo(AudioResult.BUFFERED);
    }

    @Test
    void connectionFailureIsIsolatedAndCleansUp() throws Exception {
        FakeTransportFactory factory = new FakeTransportFactory(false, true, true);
        GeminiSpeechToTextService service = service(properties(), factory);

        assertThat(service.startSession(context("transport-1", "stream-1"), transcript -> { }))
                .isEqualTo(StartResult.STARTING);

        assertThat(await(() -> service.activeSessionCount() == 0, 1_000)).isTrue();
    }

    @Test
    void connectionFailureLogsExceptionClassAndSanitizedMessage() throws Exception {
        Logger logger = (Logger) LoggerFactory.getLogger(GeminiSpeechToTextService.class);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.list = new CopyOnWriteArrayList<>();
        appender.start();
        logger.addAppender(appender);
        try {
            GeminiSttProperties properties = properties();
            properties.setApiKey("credential-must-not-be-logged");
            IllegalStateException failure = new IllegalStateException(
                    "connect failed at wss://provider.example/live?key=credential-must-not-be-logged "
                            + "Authorization: Bearer private-token caller +919876543210");
            FakeTransportFactory factory = new FakeTransportFactory(false, failure, true);
            GeminiSpeechToTextService service = service(properties, factory);

            service.startSession(context("transport-1", "stream-1"), transcript -> { });
            assertThat(await(() -> service.activeSessionCount() == 0, 1_000)).isTrue();
            assertThat(await(
                    () -> capturedLogs(appender).contains("exceptionClass=\"java.lang.IllegalStateException\""),
                    1_000)).isTrue();

            String logs = capturedLogs(appender);
            String formattedFailure = formattedFailure(
                    appender,
                    "exceptionClass=\"java.lang.IllegalStateException\"");
            assertThat(logs)
                    .contains("exceptionClass=\"java.lang.IllegalStateException\"")
                    .contains("exceptionMessage=\"")
                    .contains("[REDACTED_CREDENTIAL]")
                    .contains("[REDACTED_PHONE]")
                    .doesNotContain("credential-must-not-be-logged")
                    .doesNotContain("private-token")
                    .doesNotContain("+919876543210")
                    .doesNotContainIgnoringCase("authorization");
            assertThat(formattedFailure)
                    .contains("exceptionClass=\"java.lang.IllegalStateException\"")
                    .contains("exceptionMessage=\"")
                    .doesNotContain("credential-must-not-be-logged")
                    .doesNotContainIgnoringCase("authorization");
        } finally {
            logger.detachAppender(appender);
            appender.stop();
        }
    }

    @Test
    void handshakeFailureLogsSanitizedHttpStatusAndBody() throws Exception {
        Logger logger = (Logger) LoggerFactory.getLogger(GeminiSpeechToTextService.class);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.list = new CopyOnWriteArrayList<>();
        appender.start();
        logger.addAppender(appender);
        try {
            GeminiSttProperties properties = properties();
            properties.setApiKey("credential-must-not-be-logged");
            @SuppressWarnings("unchecked")
            HttpResponse<String> response = mock(HttpResponse.class);
            when(response.statusCode()).thenReturn(401);
            when(response.body()).thenReturn(
                    "api_key=credential-must-not-be-logged; Authorization: Bearer private-token; "
                            + "caller +919876543210; audio=" + "A".repeat(120));
            WebSocketHandshakeException failure = new WebSocketHandshakeException(response);
            FakeTransportFactory factory = new FakeTransportFactory(false, failure, true);
            GeminiSpeechToTextService service = service(properties, factory);

            service.startSession(context("transport-1", "stream-1"), transcript -> { });
            assertThat(await(() -> service.activeSessionCount() == 0, 1_000)).isTrue();
            assertThat(await(
                    () -> capturedLogs(appender).contains("httpStatus=\"401\""),
                    1_000)).isTrue();

            String logs = capturedLogs(appender);
            String formattedFailure = formattedFailure(appender, "httpStatus=401");
            assertThat(logs)
                    .contains("exceptionClass=\"java.net.http.WebSocketHandshakeException\"")
                    .contains("httpStatus=\"401\"")
                    .contains("httpBody=\"")
                    .contains("[REDACTED_CREDENTIAL]")
                    .contains("[REDACTED_PHONE]")
                    .contains("[REDACTED_CONTENT]")
                    .doesNotContain("credential-must-not-be-logged")
                    .doesNotContain("private-token")
                    .doesNotContain("+919876543210")
                    .doesNotContain("A".repeat(120))
                    .doesNotContainIgnoringCase("authorization")
                    .doesNotContainIgnoringCase("api_key");
            assertThat(formattedFailure)
                    .contains("exceptionClass=\"java.net.http.WebSocketHandshakeException\"")
                    .contains("httpStatus=401")
                    .contains("httpBody=\"")
                    .doesNotContain("credential-must-not-be-logged")
                    .doesNotContainIgnoringCase("authorization")
                    .doesNotContainIgnoringCase("api_key");
        } finally {
            logger.detachAppender(appender);
            appender.stop();
        }
    }

    @Test
    void providerCloseLogsStatusAndSanitizedReason() throws Exception {
        Logger logger = (Logger) LoggerFactory.getLogger(GeminiSpeechToTextService.class);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.list = new CopyOnWriteArrayList<>();
        appender.start();
        logger.addAppender(appender);
        try {
            GeminiSttProperties properties = properties();
            properties.setApiKey("credential-must-not-be-logged");
            FakeTransportFactory factory = new FakeTransportFactory(false);
            GeminiSpeechToTextService service = service(properties, factory);
            service.startSession(context("transport-1", "stream-1"), transcript -> { });
            FakeTransport transport = factory.awaitTransport(0);
            assertThat(await(transport::setupWasSent, 1_000)).isTrue();

            transport.disconnect(
                    1008,
                    "policy denied key=credential-must-not-be-logged caller +919876543210");
            assertThat(await(() -> service.activeSessionCount() == 0, 1_000)).isTrue();

            String logs = capturedLogs(appender);
            String formattedFailure = formattedFailure(appender, "webSocketCloseCode=1008");
            assertThat(logs)
                    .contains("webSocketCloseCode=\"1008\"")
                    .contains("webSocketCloseReason=\"")
                    .contains("[REDACTED_CREDENTIAL]")
                    .contains("[REDACTED_PHONE]")
                    .doesNotContain("credential-must-not-be-logged")
                    .doesNotContain("+919876543210");
            assertThat(formattedFailure)
                    .contains("webSocketCloseCode=1008")
                    .contains("webSocketCloseReason=\"")
                    .doesNotContain("credential-must-not-be-logged")
                    .doesNotContain("+919876543210");
        } finally {
            logger.detachAppender(appender);
            appender.stop();
        }
    }

    @Test
    void setupTimeoutIsBoundedAndCleansUp() throws Exception {
        GeminiSttProperties properties = properties();
        properties.setSetupTimeout(Duration.ofMillis(50));
        FakeTransportFactory factory = new FakeTransportFactory(false, false, false);
        GeminiSpeechToTextService service = service(properties, factory);

        service.startSession(context("transport-1", "stream-1"), transcript -> { });

        assertThat(await(() -> service.activeSessionCount() == 0, 1_000)).isTrue();
    }

    @Test
    void stopIsIdempotentAndReleasesAssociationImmediately() {
        FakeTransportFactory factory = new FakeTransportFactory(false);
        GeminiSpeechToTextService service = service(properties(), factory);
        service.startSession(context("transport-1", "stream-1"), transcript -> { });

        assertThat(service.stopSession("transport-1")).isEqualTo(StopResult.STOPPED);
        assertThat(service.stopSession("transport-1")).isEqualTo(StopResult.NOT_FOUND);
        assertThat(service.activeSessionCount()).isZero();
        assertThat(service.acceptAudio("transport-1", frame("stream-1", 16_000, new byte[320])))
                .isEqualTo(AudioResult.NO_SESSION);
    }

    @Test
    void duplicateStartDoesNotCreateAnotherTransport() {
        FakeTransportFactory factory = new FakeTransportFactory(false);
        GeminiSpeechToTextService service = service(properties(), factory);

        assertThat(service.startSession(context("transport-1", "stream-1"), transcript -> { }))
                .isEqualTo(StartResult.STARTING);
        assertThat(service.startSession(context("transport-1", "stream-1"), transcript -> { }))
                .isEqualTo(StartResult.DUPLICATE);
        assertThat(factory.transports).hasSize(1);
    }

    @Test
    void boundedQueueReportsBackpressureWithoutBlockingVoiceThread() throws Exception {
        GeminiSttProperties properties = properties();
        properties.setQueueCapacity(1);
        properties.setSendTimeout(Duration.ofMillis(300));
        FakeTransportFactory factory = new FakeTransportFactory(true);
        GeminiSpeechToTextService service = service(properties, factory);
        service.startSession(context("transport-1", "stream-1"), transcript -> { });
        FakeTransport transport = factory.awaitTransport(0);
        assertThat(await(transport::setupWasSent, 1_000)).isTrue();

        assertThat(service.acceptAudio("transport-1", frame("stream-1", 16_000, new byte[3_200])))
                .isEqualTo(AudioResult.ACCEPTED);
        assertThat(await(transport::audioSendStarted, 1_000)).isTrue();
        assertThat(service.acceptAudio("transport-1", frame("stream-1", 16_000, new byte[3_200])))
                .isEqualTo(AudioResult.ACCEPTED);
        assertThat(service.acceptAudio("transport-1", frame("stream-1", 16_000, new byte[3_200])))
                .isEqualTo(AudioResult.BACKPRESSURE);
    }

    @Test
    void invalidOrMismatchedAudioIsRejected() {
        FakeTransportFactory factory = new FakeTransportFactory(false);
        GeminiSpeechToTextService service = service(properties(), factory);
        service.startSession(context("transport-1", "stream-1"), transcript -> { });

        assertThat(service.acceptAudio("transport-1", frame("other-stream", 16_000, new byte[320])))
                .isEqualTo(AudioResult.INVALID_AUDIO);
        assertThat(service.acceptAudio("transport-1", frame("stream-1", 24_000, new byte[480])))
                .isEqualTo(AudioResult.INVALID_AUDIO);
        assertThat(service.acceptAudio("transport-1", frame("stream-1", 16_000, new byte[0])))
                .isEqualTo(AudioResult.INVALID_AUDIO);
    }

    @Test
    void credentialsAudioAndTranscriptTextNeverAppearInLogs() throws Exception {
        Logger logger = (Logger) LoggerFactory.getLogger(GeminiSpeechToTextService.class);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.list = new CopyOnWriteArrayList<>();
        appender.start();
        logger.addAppender(appender);
        try {
            GeminiSttProperties properties = properties();
            properties.setApiKey("credential-must-not-be-logged");
            FakeTransportFactory factory = new FakeTransportFactory(false);
            GeminiSpeechToTextService service = service(properties, factory);
            service.startSession(context("transport-1", "stream-1"), transcript -> { });
            FakeTransport transport = factory.awaitTransport(0);
            assertThat(await(transport::setupWasSent, 1_000)).isTrue();
            transport.emit("""
                    {"serverContent":{"inputTranscription":{"text":"private-conversation-marker"}}}
                    """);
            service.acceptAudio("transport-1", frame("stream-1", 16_000, new byte[3_200]));
            assertThat(await(() -> transport.messages.stream().anyMatch(m -> m.contains("audio/pcm")), 1_000))
                    .isTrue();

            String logs = appender.list.stream()
                    .map(event -> event.getFormattedMessage() + " " + event.getKeyValuePairs())
                    .collect(Collectors.joining("\n"));
            assertThat(logs)
                    .doesNotContain("credential-must-not-be-logged")
                    .doesNotContain("private-conversation-marker")
                    .doesNotContain("AAAAAAAA")
                    .doesNotContainIgnoringCase("authorization");
        } finally {
            logger.detachAppender(appender);
            appender.stop();
        }
    }

    private String capturedLogs(ListAppender<ILoggingEvent> appender) {
        return appender.list.stream()
                .map(event -> event.getFormattedMessage() + " " + event.getKeyValuePairs())
                .collect(Collectors.joining("\n"));
    }

    private String formattedFailure(ListAppender<ILoggingEvent> appender, String expectedDiagnostic) {
        return appender.list.stream()
                .filter(event -> event.getFormattedMessage().startsWith("Speech-to-text session failed"))
                .map(ILoggingEvent::getFormattedMessage)
                .filter(message -> message.contains(expectedDiagnostic))
                .findFirst()
                .orElse("");
    }

    private GeminiSpeechToTextService service(
            GeminiSttProperties properties,
            GeminiLiveTransportFactory factory) {
        ObjectMapper objectMapper = new ObjectMapper();
        GeminiSpeechToTextService service = new GeminiSpeechToTextService(
                properties,
                new Pcm16AudioNormalizer(),
                factory,
                new GeminiResponseParser(objectMapper),
                objectMapper,
                Clock.fixed(NOW, ZoneOffset.UTC));
        services.add(service);
        return service;
    }

    private GeminiSttProperties properties() {
        GeminiSttProperties properties = new GeminiSttProperties();
        properties.setApiKey("test-key");
        properties.setQueueCapacity(4);
        properties.setConnectTimeout(Duration.ofSeconds(1));
        properties.setSetupTimeout(Duration.ofSeconds(1));
        properties.setSendTimeout(Duration.ofSeconds(1));
        return properties;
    }

    private SttSessionContext context(String transportId, String streamSid) {
        return context(transportId, streamSid, 16_000);
    }

    private SttSessionContext context(String transportId, String streamSid, int sampleRate) {
        return new SttSessionContext(transportId, "call-1", streamSid, sampleRate, 1, 16);
    }

    private AudioFrame frame(String streamSid, int sampleRate, byte[] pcm) {
        return new AudioFrame(pcm, streamSid, 1, 1, 0, NOW, "raw", sampleRate, 1, 16);
    }

    private boolean await(BooleanSupplier condition, long timeoutMillis) throws InterruptedException {
        long deadline = System.nanoTime() + Duration.ofMillis(timeoutMillis).toNanos();
        while (System.nanoTime() < deadline) {
            if (condition.getAsBoolean()) {
                return true;
            }
            Thread.sleep(10);
        }
        return condition.getAsBoolean();
    }

    private static final class FakeTransportFactory implements GeminiLiveTransportFactory {

        private final boolean blockAudio;
        private final Throwable connectFailure;
        private final boolean autoCompleteSetup;
        private final List<FakeTransport> transports = new CopyOnWriteArrayList<>();

        private FakeTransportFactory(boolean blockAudio) {
            this(blockAudio, (Throwable) null, true);
        }

        private FakeTransportFactory(boolean blockAudio, boolean failConnect, boolean autoCompleteSetup) {
            this(
                    blockAudio,
                    failConnect ? new IllegalStateException("simulated connection failure") : null,
                    autoCompleteSetup);
        }

        private FakeTransportFactory(
                boolean blockAudio,
                Throwable connectFailure,
                boolean autoCompleteSetup) {
            this.blockAudio = blockAudio;
            this.connectFailure = connectFailure;
            this.autoCompleteSetup = autoCompleteSetup;
        }

        @Override
        public GeminiLiveTransport create() {
            FakeTransport transport = new FakeTransport(blockAudio, connectFailure, autoCompleteSetup);
            transports.add(transport);
            return transport;
        }

        private FakeTransport awaitTransport(int index) throws InterruptedException {
            long deadline = System.nanoTime() + Duration.ofSeconds(1).toNanos();
            while (transports.size() <= index && System.nanoTime() < deadline) {
                Thread.sleep(5);
            }
            return transports.get(index);
        }
    }

    private static final class FakeTransport implements GeminiLiveTransport {

        private final boolean blockAudio;
        private final Throwable connectFailure;
        private final boolean autoCompleteSetup;
        private final List<String> messages = Collections.synchronizedList(new ArrayList<>());
        private volatile Listener listener;
        private volatile URI endpoint;
        private volatile boolean closed;
        private volatile boolean audioSendStarted;

        private FakeTransport(boolean blockAudio, Throwable connectFailure, boolean autoCompleteSetup) {
            this.blockAudio = blockAudio;
            this.connectFailure = connectFailure;
            this.autoCompleteSetup = autoCompleteSetup;
        }

        @Override
        public CompletableFuture<Void> connect(URI endpoint, Listener listener) {
            this.endpoint = endpoint;
            this.listener = listener;
            if (connectFailure != null) {
                return CompletableFuture.failedFuture(connectFailure);
            }
            return CompletableFuture.completedFuture(null);
        }

        @Override
        public CompletableFuture<Void> sendText(String message) {
            messages.add(message);
            if (autoCompleteSetup && message.contains("\"setup\"")) {
                listener.onText("{\"setupComplete\":{}}");
            }
            if (message.contains("audio/pcm")) {
                audioSendStarted = true;
                if (blockAudio) {
                    return new CompletableFuture<>();
                }
            }
            return CompletableFuture.completedFuture(null);
        }

        @Override
        public CompletableFuture<Void> close() {
            closed = true;
            return CompletableFuture.completedFuture(null);
        }

        private void emit(String message) {
            listener.onText(message);
        }

        private void completeSetup() {
            listener.onText("{\"setupComplete\":{}}");
        }

        private void disconnect() {
            disconnect(1006, "provider disconnected");
        }

        private void disconnect(int statusCode, String reason) {
            listener.onClosed(statusCode, reason);
        }

        private boolean setupWasSent() {
            return messages.stream().anyMatch(message -> message.contains("\"setup\""));
        }

        private boolean audioSendStarted() {
            return audioSendStarted;
        }

        private long audioMessageCount() {
            return messages.stream().filter(message -> message.contains("audio/pcm")).count();
        }

        private List<String> audioMessages() {
            return messages.stream().filter(message -> message.contains("audio/pcm")).toList();
        }
    }
}
