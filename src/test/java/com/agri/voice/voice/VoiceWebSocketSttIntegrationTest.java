package com.agri.voice.voice;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import com.agri.voice.ai.stt.SpeechToTextService;
import com.agri.voice.ai.stt.SttSessionContext;
import com.agri.voice.ai.stt.TranscriptListener;
import com.agri.voice.voice.audio.AudioFrame;
import com.agri.voice.voice.audio.AudioFrameDecoder;
import com.fasterxml.jackson.databind.ObjectMapper;

class VoiceWebSocketSttIntegrationTest {

    private RecordingSpeechToTextService speechToText;
    private VoiceWebSocketHandler handler;
    private WebSocketSession socket;

    @BeforeEach
    void setUp() {
        speechToText = new RecordingSpeechToTextService();
        handler = new VoiceWebSocketHandler(
                new ExotelEventParser(new ObjectMapper()),
                new AudioFrameDecoder(),
                speechToText,
                Clock.fixed(Instant.EPOCH, ZoneOffset.UTC));
        socket = mock(WebSocketSession.class);
        when(socket.getId()).thenReturn("transport-1");
        when(socket.isOpen()).thenReturn(true);
    }

    @Test
    void startMediaAndStopFlowThroughTheProviderNeutralSttBoundary() throws Exception {
        handler.afterConnectionEstablished(socket);
        handler.handleMessage(socket, new TextMessage(ExotelTestMessages.start(16_000)));
        handler.handleMessage(socket, new TextMessage(
                ExotelTestMessages.media(2, 1, 100, ExotelTestMessages.pcmFrame())));
        handler.handleMessage(socket, new TextMessage(ExotelTestMessages.stop()));

        assertThat(speechToText.started).isOne();
        assertThat(speechToText.audioFrames).isOne();
        assertThat(speechToText.stopped).isOne();
        assertThat(speechToText.context.callSid()).isEqualTo(ExotelTestMessages.CALL_SID);
        assertThat(speechToText.context.streamSid()).isEqualTo(ExotelTestMessages.STREAM_SID);
        assertThat(speechToText.context.inputSampleRate()).isEqualTo(16_000);
        assertThat(speechToText.lastFrame.byteLength()).isEqualTo(320);
        assertThat(speechToText.lastFrame.sampleRate()).isEqualTo(16_000);
        assertThat(speechToText.lastFrame.channels()).isOne();
        assertThat(speechToText.lastFrame.bitsPerSample()).isEqualTo(16);
    }

    @Test
    void abnormalSocketClosureAlsoStopsTheSttSession() throws Exception {
        handler.afterConnectionEstablished(socket);
        handler.handleMessage(socket, new TextMessage(ExotelTestMessages.start(8_000)));

        handler.afterConnectionClosed(socket, CloseStatus.GOING_AWAY);

        assertThat(speechToText.started).isOne();
        assertThat(speechToText.stopped).isOne();
    }

    private static final class RecordingSpeechToTextService implements SpeechToTextService {

        private int started;
        private int audioFrames;
        private int stopped;
        private SttSessionContext context;
        private AudioFrame lastFrame;

        @Override
        public StartResult startSession(SttSessionContext context, TranscriptListener listener) {
            this.context = context;
            started++;
            return StartResult.STARTING;
        }

        @Override
        public AudioResult acceptAudio(String transportSessionId, AudioFrame frame) {
            lastFrame = frame;
            audioFrames++;
            return AudioResult.BUFFERED;
        }

        @Override
        public StopResult stopSession(String transportSessionId) {
            stopped++;
            return StopResult.STOPPED;
        }
    }
}
