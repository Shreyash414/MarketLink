package com.agri.voice.voice;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.io.IOException;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.stream.Collectors;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.slf4j.LoggerFactory;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import com.agri.voice.voice.audio.AudioFrameDecoder;
import com.fasterxml.jackson.databind.ObjectMapper;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;

class VoiceWebSocketHandlerTest {

    private static final Instant NOW = Instant.parse("2026-09-03T00:00:00Z");

    private VoiceWebSocketHandler handler;
    private WebSocketSession socketSession;
    private Logger handlerLogger;
    private ListAppender<ILoggingEvent> logAppender;

    @BeforeEach
    void setUp() {
        Clock clock = Clock.fixed(NOW, ZoneOffset.UTC);
        handler = new VoiceWebSocketHandler(
                new ExotelEventParser(new ObjectMapper()),
                new AudioFrameDecoder(),
                clock);
        socketSession = mock(WebSocketSession.class);
        when(socketSession.getId()).thenReturn("transport-1");
        when(socketSession.isOpen()).thenReturn(true);

        handlerLogger = (Logger) LoggerFactory.getLogger(VoiceWebSocketHandler.class);
        logAppender = new ListAppender<>();
        logAppender.start();
        handlerLogger.addAppender(logAppender);
    }

    @AfterEach
    void tearDown() {
        handlerLogger.detachAppender(logAppender);
        logAppender.stop();
    }

    @Test
    void connectionCreatesVoiceSession() {
        handler.afterConnectionEstablished(socketSession);

        assertThat(handler.activeSessionCount()).isOne();
        VoiceSession voiceSession = handler.findSession("transport-1").orElseThrow();
        assertThat(voiceSession.state()).isEqualTo(VoiceSession.State.OPEN);
        assertThat(voiceSession.openedAt()).isEqualTo(NOW);
    }

    @Test
    void connectedEventIsRecorded() throws Exception {
        handler.afterConnectionEstablished(socketSession);

        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.connected()));

        assertThat(handler.findSession("transport-1").orElseThrow().connectedEventReceived()).isTrue();
    }

    @ParameterizedTest
    @ValueSource(ints = {8_000, 16_000, 24_000})
    void startAcceptsEveryDocumentedSampleRate(int sampleRate) throws Exception {
        handler.afterConnectionEstablished(socketSession);

        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.start(sampleRate)));

        VoiceSession session = handler.findSession("transport-1").orElseThrow();
        assertThat(session.state()).isEqualTo(VoiceSession.State.STARTED);
        assertThat(session.callSid()).isEqualTo(ExotelTestMessages.CALL_SID);
        assertThat(session.streamSid()).isEqualTo(ExotelTestMessages.STREAM_SID);
        assertThat(session.caller()).isEqualTo("+919999999999");
        assertThat(session.destination()).isEqualTo("+918888888888");
        assertThat(session.mediaFormat().encoding()).isEqualTo("audio/x-raw");
        assertThat(session.mediaFormat().sampleRate()).isEqualTo(sampleRate);
        assertThat(session.mediaFormat().channels()).isEqualTo(1);
        assertThat(session.mediaFormat().bitsPerSample()).isEqualTo(16);
    }

    @Test
    void mediaDtmfMarkAndClearAreHandledWithoutRetainingAudio() throws Exception {
        handler.afterConnectionEstablished(socketSession);
        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.start(8_000)));

        handler.handleMessage(socketSession, new TextMessage(
                ExotelTestMessages.media(2, 1, 100, ExotelTestMessages.pcmFrame())));
        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.dtmf()));
        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.mark()));
        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.clear()));

        VoiceSession session = handler.findSession("transport-1").orElseThrow();
        assertThat(session.frameCount()).isOne();
        assertThat(session.totalAudioBytes()).isEqualTo(320);
        assertThat(session.lastFrameMetadata().sequenceNumber()).isEqualTo(2);
        assertThat(session.lastFrameMetadata().chunkNumber()).isEqualTo(1);
    }

    @Test
    void multipleMediaFramesUpdateSessionMetadata() throws Exception {
        handler.afterConnectionEstablished(socketSession);
        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.start(24_000)));

        handler.handleMessage(socketSession, new TextMessage(
                ExotelTestMessages.media(2, 1, 100, ExotelTestMessages.pcmFrame())));
        handler.handleMessage(socketSession, new TextMessage(
                ExotelTestMessages.media(3, 2, 200, ExotelTestMessages.pcmFrame())));

        VoiceSession session = handler.findSession("transport-1").orElseThrow();
        assertThat(session.frameCount()).isEqualTo(2);
        assertThat(session.totalAudioBytes()).isEqualTo(640);
        assertThat(session.lastFrameMetadata().timestampMilliseconds()).isEqualTo(200);
    }

    @Test
    void stopClosesSocketAndImmediatelyReleasesSession() throws Exception {
        handler.afterConnectionEstablished(socketSession);
        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.start(8_000)));

        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.stop()));

        assertThat(handler.activeSessionCount()).isZero();
        verify(socketSession).close(CloseStatus.NORMAL);
    }

    @Test
    void malformedUnknownAndMissingEventMessagesCannotBreakConnection() {
        handler.afterConnectionEstablished(socketSession);

        assertThatCode(() -> {
            handler.handleMessage(socketSession, new TextMessage("{broken"));
            handler.handleMessage(socketSession, new TextMessage("{\"event\":\"unknown\"}"));
            handler.handleMessage(socketSession, new TextMessage("{\"stream_sid\":\"MZ-test\"}"));
        }).doesNotThrowAnyException();
        assertThat(handler.activeSessionCount()).isOne();
    }

    @Test
    void missingStartFieldsDoNotCreateStartedSession() throws Exception {
        handler.afterConnectionEstablished(socketSession);

        handler.handleMessage(socketSession, new TextMessage("{\"event\":\"start\",\"start\":{}}"));

        assertThat(handler.findSession("transport-1").orElseThrow().state())
                .isEqualTo(VoiceSession.State.OPEN);
    }

    @Test
    void invalidBase64IsIgnoredWithoutChangingFrameCount() throws Exception {
        handler.afterConnectionEstablished(socketSession);
        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.start(8_000)));
        String invalidMedia = """
                {
                  "event":"media",
                  "sequence_number":2,
                  "stream_sid":"MZ-test-stream",
                  "media":{"chunk":1,"timestamp":100,"payload":"invalid%%%"}
                }
                """;

        handler.handleMessage(socketSession, new TextMessage(invalidMedia));

        assertThat(handler.findSession("transport-1").orElseThrow().frameCount()).isZero();
    }

    @Test
    void duplicateAndUnexpectedStopMessagesAreSafe() {
        handler.afterConnectionEstablished(socketSession);

        assertThatCode(() -> {
            handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.stop()));
            handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.stop()));
        }).doesNotThrowAnyException();
        assertThat(handler.activeSessionCount()).isZero();
    }

    @Test
    void connectionCloseReleasesSessionResources() throws Exception {
        handler.afterConnectionEstablished(socketSession);
        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.start(8_000)));

        handler.afterConnectionClosed(socketSession, CloseStatus.GOING_AWAY);

        assertThat(handler.activeSessionCount()).isZero();
    }

    @Test
    void lateTransportErrorAfterStopIsSafe() throws Exception {
        handler.afterConnectionEstablished(socketSession);
        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.start(8_000)));
        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.stop()));

        assertThatCode(() -> handler.handleTransportError(socketSession, new IOException("late close")))
                .doesNotThrowAnyException();
        assertThat(handler.activeSessionCount()).isZero();
    }

    @Test
    void credentialsPersonalDataAndRawAudioNeverAppearInHandlerLogs() throws Exception {
        handler.afterConnectionEstablished(socketSession);
        String rawAudioMarker = "raw-audio-must-not-be-logged";
        String encodedAudioMarker = java.util.Base64.getEncoder()
                .encodeToString(rawAudioMarker.getBytes(java.nio.charset.StandardCharsets.UTF_8));
        String untrustedMessage = """
                {
                  "event":"not-supported",
                  "authorization":"Basic secret-token-value",
                  "api_key":"api-key-secret",
                  "media":{"payload":"%s"}
                }
                """.formatted(encodedAudioMarker);

        handler.handleMessage(socketSession, new TextMessage(ExotelTestMessages.start(8_000)));
        handler.handleMessage(socketSession, new TextMessage(untrustedMessage));

        String capturedLogs = logAppender.list.stream()
                .map(this::renderLogEvent)
                .collect(Collectors.joining("\n"));
        assertThat(capturedLogs)
                .doesNotContain("secret-token-value")
                .doesNotContain("api-key-secret")
                .doesNotContain(rawAudioMarker)
                .doesNotContain(encodedAudioMarker)
                .doesNotContain("+919999999999")
                .doesNotContain("+918888888888")
                .doesNotContainIgnoringCase("authorization");
        assertThat(capturedLogs)
                .contains(ExotelTestMessages.CALL_SID)
                .contains(ExotelTestMessages.STREAM_SID);
    }

    private String renderLogEvent(ILoggingEvent event) {
        return event.getFormattedMessage() + " " + event.getKeyValuePairs();
    }
}
