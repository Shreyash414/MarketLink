package com.agri.voice.ai.conversation;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import jakarta.annotation.PreDestroy;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Component;

import com.agri.voice.ai.llm.LLMMessage;
import com.agri.voice.ai.llm.LLMRequest;
import com.agri.voice.ai.llm.LLMResponse;
import com.agri.voice.ai.llm.LLMRole;
import com.agri.voice.ai.llm.LLMService;
import com.agri.voice.ai.stt.Transcript;
import com.agri.voice.ai.stt.TranscriptType;

@Component
@EnableConfigurationProperties(ConversationProperties.class)
public class ConversationManager {

    private static final Logger log = LoggerFactory.getLogger(ConversationManager.class);

    private final LLMService llmService;
    private final ConversationProperties properties;
    private final String systemInstruction;
    private final ExecutorService executor;
    private final ConcurrentMap<String, SessionState> sessions = new ConcurrentHashMap<>();

    @Autowired
    ConversationManager(
            LLMService llmService,
            ConversationProperties properties,
            AgriculturalAssistantPrompt prompt) {
        this(llmService, properties, prompt, Executors.newVirtualThreadPerTaskExecutor());
    }

    ConversationManager(
            LLMService llmService,
            ConversationProperties properties,
            AgriculturalAssistantPrompt prompt,
            ExecutorService executor) {
        validate(properties);
        this.llmService = llmService;
        this.properties = properties;
        this.systemInstruction = prompt.text();
        this.executor = executor;
    }

    public StartResult startSession(String conversationId, AssistantResponseListener listener) {
        if (!hasText(conversationId) || listener == null) {
            return StartResult.INVALID;
        }
        SessionState state = new SessionState(conversationId, listener);
        return sessions.putIfAbsent(conversationId, state) == null ? StartResult.STARTED : StartResult.DUPLICATE;
    }

    public TranscriptResult acceptTranscript(Transcript transcript) {
        if (transcript == null || transcript.type() != TranscriptType.FINAL || !hasText(transcript.text())) {
            return TranscriptResult.IGNORED;
        }
        SessionState state = sessions.get(transcript.transportSessionId());
        if (state == null) {
            return TranscriptResult.NO_SESSION;
        }

        synchronized (state) {
            if (state.closed) {
                return TranscriptResult.NO_SESSION;
            }
            if (!state.rememberSequence(transcript.sequenceNumber(), properties.getDuplicateWindowSize())) {
                return TranscriptResult.DUPLICATE;
            }
            String userText = truncate(transcript.text().trim(), effectiveMessageLimit());
            state.tail = state.tail.handleAsync((unused, failure) -> null, executor)
                    .thenCompose(unused -> processTurn(state, userText));
            return TranscriptResult.ACCEPTED;
        }
    }

    public CloseResult closeSession(String conversationId) {
        if (!hasText(conversationId)) {
            return CloseResult.NOT_FOUND;
        }
        SessionState state = sessions.remove(conversationId);
        if (state == null) {
            return CloseResult.NOT_FOUND;
        }
        synchronized (state) {
            state.closed = true;
            state.history.clear();
            state.sequences.clear();
        }
        return CloseResult.CLOSED;
    }

    public int activeSessionCount() {
        return sessions.size();
    }

    List<LLMMessage> history(String conversationId) {
        SessionState state = sessions.get(conversationId);
        if (state == null) {
            return List.of();
        }
        synchronized (state) {
            return List.copyOf(state.history);
        }
    }

    private CompletableFuture<Void> processTurn(SessionState state, String userText) {
        LLMRequest request;
        synchronized (state) {
            if (state.closed) {
                return CompletableFuture.completedFuture(null);
            }
            state.history.addLast(new LLMMessage(LLMRole.USER, userText));
            trimHistory(state.history);
            request = new LLMRequest(state.conversationId, systemInstruction, new ArrayList<>(state.history));
        }

        CompletableFuture<LLMResponse> responseFuture;
        try {
            responseFuture = llmService.generate(request);
            if (responseFuture == null) {
                responseFuture = CompletableFuture.completedFuture(
                        LLMResponse.failure(LLMResponse.Status.NETWORK_FAILURE, null));
            }
        } catch (RuntimeException exception) {
            responseFuture = CompletableFuture.completedFuture(
                    LLMResponse.failure(LLMResponse.Status.NETWORK_FAILURE, null));
        }
        return responseFuture.exceptionally(failure -> LLMResponse.failure(LLMResponse.Status.NETWORK_FAILURE, null))
                .thenAccept(response -> completeTurn(state, response));
    }

    private void completeTurn(SessionState state, LLMResponse response) {
        boolean fallback = !response.successful();
        String assistantText = fallback
                ? properties.getFallbackResponse().trim()
                : truncate(response.text(), effectiveMessageLimit());
        AssistantResponse result;
        synchronized (state) {
            if (state.closed || sessions.get(state.conversationId) != state) {
                return;
            }
            state.history.addLast(new LLMMessage(LLMRole.ASSISTANT, assistantText));
            trimHistory(state.history);
            result = new AssistantResponse(state.conversationId, assistantText, fallback, response.status());
        }

        try {
            state.listener.onResponse(result);
        } catch (RuntimeException exception) {
            log.atWarn()
                    .addKeyValue("conversationId", state.conversationId)
                    .addKeyValue("reason", "response_listener_failure")
                    .log("Assistant response listener failed");
        }
    }

    private void trimHistory(Deque<LLMMessage> history) {
        while (history.size() > properties.getMaxMessages() || characterCount(history) > properties.getMaxContextCharacters()) {
            history.removeFirst();
        }
    }

    private int characterCount(Deque<LLMMessage> history) {
        int count = 0;
        for (LLMMessage message : history) {
            count += message.text().length();
        }
        return count;
    }

    private String truncate(String text, int limit) {
        String value = text == null ? "" : text.trim();
        return value.length() <= limit ? value : value.substring(0, limit);
    }

    private int effectiveMessageLimit() {
        return Math.min(properties.getMaxMessageCharacters(), properties.getMaxContextCharacters());
    }

    @PreDestroy
    void shutdown() {
        for (String conversationId : List.copyOf(sessions.keySet())) {
            closeSession(conversationId);
        }
        executor.close();
    }

    private void validate(ConversationProperties values) {
        if (values.getMaxMessages() < 2
                || values.getMaxContextCharacters() < 1
                || values.getMaxMessageCharacters() < 1
                || values.getDuplicateWindowSize() < 1
                || !hasText(values.getFallbackResponse())) {
            throw new IllegalArgumentException("Conversation limits and fallback response must be valid");
        }
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    public enum StartResult {
        STARTED,
        DUPLICATE,
        INVALID
    }

    public enum TranscriptResult {
        ACCEPTED,
        IGNORED,
        DUPLICATE,
        NO_SESSION
    }

    public enum CloseResult {
        CLOSED,
        NOT_FOUND
    }

    private static final class SessionState {

        private final String conversationId;
        private final AssistantResponseListener listener;
        private final Deque<LLMMessage> history = new ArrayDeque<>();
        private final Set<Long> sequences = new LinkedHashSet<>();
        private CompletableFuture<Void> tail = CompletableFuture.completedFuture(null);
        private boolean closed;

        private SessionState(String conversationId, AssistantResponseListener listener) {
            this.conversationId = conversationId;
            this.listener = listener;
        }

        private boolean rememberSequence(long sequence, int windowSize) {
            if (!sequences.add(sequence)) {
                return false;
            }
            if (sequences.size() > windowSize) {
                Long oldest = sequences.iterator().next();
                sequences.remove(oldest);
            }
            return true;
        }
    }
}
