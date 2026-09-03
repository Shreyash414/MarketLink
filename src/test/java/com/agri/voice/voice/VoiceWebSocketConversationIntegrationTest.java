package com.agri.voice.voice;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.io.IOException;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import com.agri.voice.ai.conversation.AssistantResponseListener;
import com.agri.voice.ai.conversation.ConversationManager;
import com.agri.voice.ai.stt.SpeechToTextService;
import com.agri.voice.ai.stt.SttSessionContext;
import com.agri.voice.ai.stt.Transcript;
import com.agri.voice.ai.stt.TranscriptListener;
import com.agri.voice.ai.stt.TranscriptType;
import com.agri.voice.voice.audio.AudioFrame;
import com.agri.voice.voice.audio.AudioFrameDecoder;
import com.fasterxml.jackson.databind.ObjectMapper;

class VoiceWebSocketConversationIntegrationTest {

    private RecordingStt speechToText;
    private ConversationManager conversationManager;
    private VoiceWebSocketHandler handler;
    private WebSocketSession socket;

    @BeforeEach
    void setUp() {
        speechToText = new RecordingStt();
        conversationManager = mock(ConversationManager.class);
        when(conversationManager.startSession(eq("transport-1"), any(AssistantResponseListener.class)))
                .thenReturn(ConversationManager.StartResult.STARTED);
        when(conversationManager.acceptTranscript(any(Transcript.class)))
                .thenReturn(ConversationManager.TranscriptResult.ACCEPTED);
        handler = new VoiceWebSocketHandler(
                new ExotelEventParser(new ObjectMapper()),
                new AudioFrameDecoder(),
                speechToText,
                conversationManager,
                Clock.fixed(Instant.EPOCH, ZoneOffset.UTC));
        socket = mock(WebSocketSession.class);
        when(socket.getId()).thenReturn("transport-1");
        when(socket.isOpen()).thenReturn(true);
    }

    @Test
    void finalTranscriptCrossesProviderNeutralConversationBoundary() throws Exception {
        start();
        Transcript interim = transcript(TranscriptType.INTERIM, "gehun", 1);
        Transcript complete = transcript(TranscriptType.FINAL, "gehun ka bhav", 2);

        speechToText.listener.onTranscript(interim);
        speechToText.listener.onTranscript(complete);

        verify(conversationManager).startSession(eq("transport-1"), any(AssistantResponseListener.class));
        verify(conversationManager).acceptTranscript(interim);
        verify(conversationManager).acceptTranscript(complete);
    }

    @Test
    void stopReleasesConversationExactlyOnce() throws Exception {
        start();

        handler.handleMessage(socket, new TextMessage(ExotelTestMessages.stop()));

        verify(conversationManager).closeSession("transport-1");
    }

    @Test
    void disconnectAndTransportErrorReleaseConversation() throws Exception {
        start();
        handler.afterConnectionClosed(socket, CloseStatus.GOING_AWAY);
        verify(conversationManager).closeSession("transport-1");

        resetWithNewSession();
        start();
        handler.handleTransportError(socket, new IOException("safe test failure"));
        verify(conversationManager).closeSession("transport-1");
    }

    @Test
    void rejectedSttStartImmediatelyReleasesConversation() throws Exception {
        speechToText.startResult = SpeechToTextService.StartResult.REJECTED;
        start();

        verify(conversationManager).closeSession("transport-1");
        verify(conversationManager, never()).acceptTranscript(any());
    }

    private void start() throws Exception {
        handler.afterConnectionEstablished(socket);
        handler.handleMessage(socket, new TextMessage(ExotelTestMessages.start(16_000)));
    }

    private void resetWithNewSession() {
        conversationManager = mock(ConversationManager.class);
        when(conversationManager.startSession(eq("transport-1"), any(AssistantResponseListener.class)))
                .thenReturn(ConversationManager.StartResult.STARTED);
        handler = new VoiceWebSocketHandler(
                new ExotelEventParser(new ObjectMapper()),
                new AudioFrameDecoder(),
                speechToText,
                conversationManager,
                Clock.fixed(Instant.EPOCH, ZoneOffset.UTC));
    }

    private Transcript transcript(TranscriptType type, String text, long sequence) {
        return new Transcript(
                "transport-1",
                ExotelTestMessages.CALL_SID,
                ExotelTestMessages.STREAM_SID,
                text,
                type,
                Instant.EPOCH,
                "hi-IN",
                sequence);
    }

    private static final class RecordingStt implements SpeechToTextService {

        private TranscriptListener listener;
        private StartResult startResult = StartResult.STARTING;

        @Override
        public StartResult startSession(SttSessionContext context, TranscriptListener listener) {
            this.listener = listener;
            return startResult;
        }

        @Override
        public AudioResult acceptAudio(String transportSessionId, AudioFrame frame) {
            return AudioResult.ACCEPTED;
        }

        @Override
        public StopResult stopSession(String transportSessionId) {
            return StopResult.STOPPED;
        }
    }
}
