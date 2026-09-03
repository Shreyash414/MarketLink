package com.agri.voice.voice;

import java.io.IOException;
import java.time.Clock;
import java.time.Instant;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import com.agri.voice.ai.conversation.AssistantResponse;
import com.agri.voice.ai.conversation.ConversationManager;
import com.agri.voice.ai.stt.NoOpSpeechToTextService;
import com.agri.voice.ai.stt.SpeechToTextService;
import com.agri.voice.ai.stt.SttSessionContext;
import com.agri.voice.ai.stt.Transcript;
import com.agri.voice.voice.ExotelEventParser.ParseResult;
import com.agri.voice.voice.audio.AudioFrame;
import com.agri.voice.voice.audio.AudioFrameDecoder;
import com.agri.voice.voice.audio.AudioFrameDecoder.DecodeResult;
import com.agri.voice.voice.dto.ClearEvent;
import com.agri.voice.voice.dto.ConnectedEvent;
import com.agri.voice.voice.dto.DtmfEvent;
import com.agri.voice.voice.dto.MarkEvent;
import com.agri.voice.voice.dto.MediaEvent;
import com.agri.voice.voice.dto.StartEvent;
import com.agri.voice.voice.dto.StopEvent;

@Component
public class VoiceWebSocketHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(VoiceWebSocketHandler.class);
    private static final Set<Integer> SUPPORTED_SAMPLE_RATES = Set.of(8_000, 16_000, 24_000);
    private static final Set<String> SUPPORTED_ENCODINGS = Set.of(
            "raw", "audio/x-raw", "slin", "audio/slin", "audio/x-slin");
    private static final int EXOTEL_CHANNELS = 1;
    private static final int EXOTEL_BITS_PER_SAMPLE = 16;

    private final ExotelEventParser eventParser;
    private final AudioFrameDecoder audioFrameDecoder;
    private final SpeechToTextService speechToTextService;
    private final ConversationManager conversationManager;
    private final Clock clock;
    private final ConcurrentMap<String, VoiceSession> sessions = new ConcurrentHashMap<>();

    @Autowired
    public VoiceWebSocketHandler(
            ExotelEventParser eventParser,
            AudioFrameDecoder audioFrameDecoder,
            SpeechToTextService speechToTextService,
            ConversationManager conversationManager) {
        this(eventParser, audioFrameDecoder, speechToTextService, conversationManager, Clock.systemUTC());
    }

    VoiceWebSocketHandler(
            ExotelEventParser eventParser,
            AudioFrameDecoder audioFrameDecoder,
            Clock clock) {
        this(eventParser, audioFrameDecoder, NoOpSpeechToTextService.INSTANCE, null, clock);
    }

    VoiceWebSocketHandler(
            ExotelEventParser eventParser,
            AudioFrameDecoder audioFrameDecoder,
            SpeechToTextService speechToTextService,
            Clock clock) {
        this(eventParser, audioFrameDecoder, speechToTextService, null, clock);
    }

    VoiceWebSocketHandler(
            ExotelEventParser eventParser,
            AudioFrameDecoder audioFrameDecoder,
            SpeechToTextService speechToTextService,
            ConversationManager conversationManager,
            Clock clock) {
        this.eventParser = eventParser;
        this.audioFrameDecoder = audioFrameDecoder;
        this.speechToTextService = speechToTextService;
        this.conversationManager = conversationManager;
        this.clock = clock;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession socketSession) {
        VoiceSession voiceSession = new VoiceSession(socketSession.getId(), Instant.now(clock));
        VoiceSession existing = sessions.putIfAbsent(socketSession.getId(), voiceSession);
        if (existing != null) {
            log.atWarn()
                    .addKeyValue("transportSessionId", socketSession.getId())
                    .addKeyValue("reason", "duplicate_transport_session")
                    .log("WebSocket connection rejected");
            closeQuietly(socketSession, CloseStatus.POLICY_VIOLATION);
            return;
        }

        log.atInfo()
                .addKeyValue("transportSessionId", socketSession.getId())
                .log("Voice WebSocket connected");
    }

    @Override
    protected void handleTextMessage(WebSocketSession socketSession, TextMessage message) {
        VoiceSession voiceSession = sessions.get(socketSession.getId());
        if (voiceSession == null) {
            log.atWarn()
                    .addKeyValue("transportSessionId", socketSession.getId())
                    .addKeyValue("reason", "no_active_session")
                    .log("WebSocket message ignored");
            return;
        }

        ParseResult parsed = eventParser.parse(message.getPayload());
        if (!parsed.successful()) {
            log.atWarn()
                    .addKeyValue("transportSessionId", socketSession.getId())
                    .addKeyValue("reason", parsed.error())
                    .addKeyValue("messageLength", message.getPayloadLength())
                    .log("Exotel event rejected");
            return;
        }

        try {
            switch (parsed.type()) {
                case CONNECTED -> handleConnected(voiceSession, (ConnectedEvent) parsed.event());
                case START -> handleStart(voiceSession, (StartEvent) parsed.event());
                case MEDIA -> handleMedia(voiceSession, (MediaEvent) parsed.event());
                case DTMF -> handleDtmf(voiceSession, (DtmfEvent) parsed.event());
                case STOP -> handleStop(socketSession, voiceSession, (StopEvent) parsed.event());
                case MARK -> handleMark(voiceSession, (MarkEvent) parsed.event());
                case CLEAR -> handleClear(voiceSession, (ClearEvent) parsed.event());
            }
        } catch (RuntimeException exception) {
            log.atError()
                    .addKeyValue("transportSessionId", socketSession.getId())
                    .addKeyValue("callSid", voiceSession.callSid())
                    .addKeyValue("streamSid", voiceSession.streamSid())
                    .addKeyValue("reason", "event_processing_failure")
                    .log("Exotel event could not be processed");
        }
    }

    private void handleConnected(VoiceSession session, ConnectedEvent event) {
        VoiceSession.ConnectedResult result = session.recordConnectedEvent();
        log.atInfo()
                .addKeyValue("transportSessionId", session.transportSessionId())
                .addKeyValue("result", result)
                .log("Exotel connected event handled");
    }

    private void handleStart(VoiceSession session, StartEvent event) {
        Optional<VoiceSession.StartDetails> details = toStartDetails(event);
        if (details.isEmpty()) {
            log.atWarn()
                    .addKeyValue("transportSessionId", session.transportSessionId())
                    .addKeyValue("reason", "invalid_start_fields")
                    .log("Exotel start event rejected");
            return;
        }

        VoiceSession.StartResult result = session.start(details.get(), Instant.now(clock));
        log.atInfo()
                .addKeyValue("transportSessionId", session.transportSessionId())
                .addKeyValue("callSid", details.get().callSid())
                .addKeyValue("streamSid", details.get().streamSid())
                .addKeyValue("sampleRate", details.get().mediaFormat().sampleRate())
                .addKeyValue("result", result)
                .log("Exotel start event handled");

        if (result == VoiceSession.StartResult.STARTED) {
            ConversationManager.StartResult conversationResult = conversationManager == null
                    ? ConversationManager.StartResult.STARTED
                    : conversationManager.startSession(session.transportSessionId(), this::handleAssistantResponse);
            VoiceSession.MediaFormat format = details.get().mediaFormat();
            SpeechToTextService.StartResult sttResult = speechToTextService.startSession(
                    new SttSessionContext(
                            session.transportSessionId(),
                            details.get().callSid(),
                            details.get().streamSid(),
                            format.sampleRate(),
                            format.channels(),
                            format.bitsPerSample()),
                    this::handleTranscript);
            log.atInfo()
                    .addKeyValue("transportSessionId", session.transportSessionId())
                    .addKeyValue("callSid", details.get().callSid())
                    .addKeyValue("streamSid", details.get().streamSid())
                    .addKeyValue("result", sttResult)
                    .addKeyValue("conversationResult", conversationResult)
                    .log("Speech-to-text start requested");
            if (sttResult != SpeechToTextService.StartResult.STARTING) {
                closeConversation(session.transportSessionId());
            }
        }
    }

    private void handleMedia(VoiceSession session, MediaEvent event) {
        DecodeResult decoded = audioFrameDecoder.decode(event, session);
        if (!decoded.successful()) {
            log.atWarn()
                    .addKeyValue("transportSessionId", session.transportSessionId())
                    .addKeyValue("callSid", session.callSid())
                    .addKeyValue("streamSid", session.streamSid())
                    .addKeyValue("reason", decoded.error())
                    .log("Exotel media event rejected");
            return;
        }

        AudioFrame frame = decoded.frame();
        VoiceSession.FrameResult result = session.recordFrame(frame);
        SpeechToTextService.AudioResult sttResult = result == VoiceSession.FrameResult.RECORDED
                ? speechToTextService.acceptAudio(session.transportSessionId(), frame)
                : SpeechToTextService.AudioResult.INVALID_AUDIO;
        log.atDebug()
                .addKeyValue("transportSessionId", session.transportSessionId())
                .addKeyValue("callSid", session.callSid())
                .addKeyValue("streamSid", session.streamSid())
                .addKeyValue("sequenceNumber", frame.sequenceNumber())
                .addKeyValue("chunkNumber", frame.chunkNumber())
                .addKeyValue("audioBytes", frame.byteLength())
                .addKeyValue("result", result)
                .addKeyValue("speechToTextResult", sttResult)
                .log("Exotel media frame handled");
    }

    private void handleDtmf(VoiceSession session, DtmfEvent event) {
        boolean valid = session.state() == VoiceSession.State.STARTED
                && streamMatches(session, event.streamSid())
                && event.dtmf() != null
                && hasText(event.dtmf().digit());
        log.atDebug()
                .addKeyValue("transportSessionId", session.transportSessionId())
                .addKeyValue("callSid", session.callSid())
                .addKeyValue("streamSid", session.streamSid())
                .addKeyValue("result", valid ? "accepted" : "ignored")
                .log("Exotel DTMF event handled");
    }

    private void handleMark(VoiceSession session, MarkEvent event) {
        boolean valid = session.state() == VoiceSession.State.STARTED
                && streamMatches(session, event.streamSid())
                && event.mark() != null
                && hasText(event.mark().name());
        log.atDebug()
                .addKeyValue("transportSessionId", session.transportSessionId())
                .addKeyValue("callSid", session.callSid())
                .addKeyValue("streamSid", session.streamSid())
                .addKeyValue("result", valid ? "accepted" : "ignored")
                .log("Exotel mark event handled");
    }

    private void handleClear(VoiceSession session, ClearEvent event) {
        boolean valid = session.state() == VoiceSession.State.STARTED
                && streamMatches(session, event.streamSid());
        log.atWarn()
                .addKeyValue("transportSessionId", session.transportSessionId())
                .addKeyValue("callSid", session.callSid())
                .addKeyValue("streamSid", session.streamSid())
                .addKeyValue("direction", "inbound")
                .addKeyValue("result", valid ? "ignored_outbound_only_event" : "ignored_invalid_event")
                .log("Exotel clear event handled");
    }

    private void handleStop(WebSocketSession socketSession, VoiceSession session, StopEvent event) {
        if (hasText(event.streamSid()) && hasText(session.streamSid())
                && !event.streamSid().equals(session.streamSid())) {
            log.atWarn()
                    .addKeyValue("transportSessionId", session.transportSessionId())
                    .addKeyValue("callSid", session.callSid())
                    .addKeyValue("streamSid", session.streamSid())
                    .addKeyValue("reason", "stream_mismatch")
                    .log("Exotel stop event rejected");
            return;
        }

        String reason = event.stop() == null ? null : event.stop().reason();
        VoiceSession.StopResult result = session.stop(reason, Instant.now(clock));
        String callSid = session.callSid();
        String streamSid = session.streamSid();
        speechToTextService.stopSession(session.transportSessionId());
        closeConversation(session.transportSessionId());
        sessions.remove(socketSession.getId(), session);
        session.close();

        log.atInfo()
                .addKeyValue("transportSessionId", socketSession.getId())
                .addKeyValue("callSid", callSid)
                .addKeyValue("streamSid", streamSid)
                .addKeyValue("result", result)
                .log("Exotel stop event handled and voice session released");
        closeQuietly(socketSession, CloseStatus.NORMAL);
    }

    private Optional<VoiceSession.StartDetails> toStartDetails(StartEvent event) {
        if (event == null || event.start() == null || event.start().mediaFormat() == null) {
            return Optional.empty();
        }

        StartEvent.StartPayload start = event.start();
        String effectiveStreamSid = hasText(start.streamSid()) ? start.streamSid() : event.streamSid();
        if (!hasText(effectiveStreamSid)
                || (hasText(event.streamSid()) && !event.streamSid().equals(effectiveStreamSid))
                || !hasText(start.callSid())
                || !hasText(start.from())
                || !hasText(start.to())
                || !hasText(start.mediaFormat().encoding())
                || !hasText(start.mediaFormat().sampleRate())) {
            return Optional.empty();
        }

        String encoding = start.mediaFormat().encoding().trim().toLowerCase(Locale.ROOT);
        if (!SUPPORTED_ENCODINGS.contains(encoding)) {
            return Optional.empty();
        }

        int sampleRate;
        try {
            sampleRate = Integer.parseInt(start.mediaFormat().sampleRate());
        } catch (NumberFormatException exception) {
            return Optional.empty();
        }
        if (!SUPPORTED_SAMPLE_RATES.contains(sampleRate)) {
            return Optional.empty();
        }

        VoiceSession.MediaFormat format = new VoiceSession.MediaFormat(
                encoding,
                sampleRate,
                EXOTEL_CHANNELS,
                EXOTEL_BITS_PER_SAMPLE);
        return Optional.of(new VoiceSession.StartDetails(
                start.callSid(),
                effectiveStreamSid,
                start.accountSid(),
                start.from(),
                start.to(),
                format));
    }

    private boolean streamMatches(VoiceSession session, String eventStreamSid) {
        return hasText(eventStreamSid) && eventStreamSid.equals(session.streamSid());
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    @Override
    public void afterConnectionClosed(WebSocketSession socketSession, CloseStatus status) {
        VoiceSession session = sessions.remove(socketSession.getId());
        if (session == null) {
            return;
        }

        String callSid = session.callSid();
        String streamSid = session.streamSid();
        speechToTextService.stopSession(session.transportSessionId());
        closeConversation(session.transportSessionId());
        session.close();
        log.atInfo()
                .addKeyValue("transportSessionId", socketSession.getId())
                .addKeyValue("callSid", callSid)
                .addKeyValue("streamSid", streamSid)
                .addKeyValue("closeCode", status.getCode())
                .log("Voice WebSocket closed and session released");
    }

    @Override
    public void handleTransportError(WebSocketSession socketSession, Throwable exception) {
        VoiceSession session = sessions.remove(socketSession.getId());
        if (session == null) {
            log.atDebug()
                    .addKeyValue("transportSessionId", socketSession.getId())
                    .addKeyValue("reason", "transport_error_after_cleanup")
                    .log("Voice WebSocket transport callback ignored");
            return;
        }

        String callSid = session.callSid();
        String streamSid = session.streamSid();
        speechToTextService.stopSession(session.transportSessionId());
        closeConversation(session.transportSessionId());
        session.close();

        log.atWarn()
                .addKeyValue("transportSessionId", socketSession.getId())
                .addKeyValue("callSid", callSid)
                .addKeyValue("streamSid", streamSid)
                .addKeyValue("reason", "transport_error")
                .log("Voice WebSocket transport failed and session released");
        closeQuietly(socketSession, CloseStatus.SERVER_ERROR);
    }

    int activeSessionCount() {
        return sessions.size();
    }

    Optional<VoiceSession> findSession(String transportSessionId) {
        return Optional.ofNullable(sessions.get(transportSessionId));
    }

    private void handleTranscript(Transcript transcript) {
        log.atDebug()
                .addKeyValue("transportSessionId", transcript.transportSessionId())
                .addKeyValue("callSid", transcript.callSid())
                .addKeyValue("streamSid", transcript.streamSid())
                .addKeyValue("transcriptType", transcript.type())
                .addKeyValue("characterCount", transcript.text().length())
                .addKeyValue("sequenceNumber", transcript.sequenceNumber())
                .log("Voice transcript received");
        if (conversationManager != null) {
            ConversationManager.TranscriptResult result = conversationManager.acceptTranscript(transcript);
            log.atDebug()
                    .addKeyValue("transportSessionId", transcript.transportSessionId())
                    .addKeyValue("transcriptType", transcript.type())
                    .addKeyValue("result", result)
                    .log("Voice transcript routed to conversation");
        }
    }

    private void handleAssistantResponse(AssistantResponse response) {
        log.atInfo()
                .addKeyValue("transportSessionId", response.conversationId())
                .addKeyValue("fallback", response.fallback())
                .addKeyValue("status", response.status())
                .addKeyValue("characterCount", response.text().length())
                .log("Assistant text response ready transportSessionId={} fallback={} status={} characterCount={}",
                        response.conversationId(), response.fallback(), response.status(), response.text().length());
    }

    private void closeConversation(String transportSessionId) {
        if (conversationManager != null) {
            conversationManager.closeSession(transportSessionId);
        }
    }

    private void closeQuietly(WebSocketSession session, CloseStatus status) {
        try {
            if (session.isOpen()) {
                session.close(status);
            }
        } catch (IOException exception) {
            log.atWarn()
                    .addKeyValue("transportSessionId", session.getId())
                    .addKeyValue("reason", "close_failed")
                    .log("Voice WebSocket could not be closed cleanly");
        }
    }
}
