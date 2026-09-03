package com.agri.voice.ai.conversation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.agri.voice.ai.llm.LLMMessage;
import com.agri.voice.ai.llm.LLMRequest;
import com.agri.voice.ai.llm.LLMResponse;
import com.agri.voice.ai.llm.LLMRole;
import com.agri.voice.ai.llm.LLMService;
import com.agri.voice.ai.stt.Transcript;
import com.agri.voice.ai.stt.TranscriptType;

class ConversationManagerTest {

    private ConversationProperties properties;
    private ControlledLlmService llmService;
    private ConversationManager manager;

    @BeforeEach
    void setUp() {
        properties = new ConversationProperties();
        llmService = new ControlledLlmService();
        manager = new ConversationManager(llmService, properties, new AgriculturalAssistantPrompt(properties));
    }

    @AfterEach
    void tearDown() {
        manager.shutdown();
    }

    @Test
    void finalTranscriptProducesAssistantResponseAndBoundedHistory() throws Exception {
        List<AssistantResponse> responses = new CopyOnWriteArrayList<>();
        manager.startSession("call-a", responses::add);
        llmService.addResponse(LLMResponse.success("Aap fasal ko sukha rakhein."));

        assertThat(manager.acceptTranscript(transcript("call-a", TranscriptType.FINAL, "Gehu kaise rakhein?", 1)))
                .isEqualTo(ConversationManager.TranscriptResult.ACCEPTED);
        await(() -> responses.size() == 1);

        assertThat(llmService.requests).hasSize(1);
        assertThat(llmService.requests.get(0).messages())
                .extracting(LLMMessage::role, LLMMessage::text)
                .containsExactly(org.assertj.core.groups.Tuple.tuple(LLMRole.USER, "Gehu kaise rakhein?"));
        assertThat(responses.get(0).text()).isEqualTo("Aap fasal ko sukha rakhein.");
        assertThat(responses.get(0).fallback()).isFalse();
        assertThat(manager.history("call-a")).extracting(LLMMessage::role)
                .containsExactly(LLMRole.USER, LLMRole.ASSISTANT);
    }

    @Test
    void interimDuplicateUnknownAndMissingSessionsNeverCallLlm() {
        manager.startSession("call-a", ignored -> { });

        assertThat(manager.acceptTranscript(transcript("call-a", TranscriptType.INTERIM, "interim", 1)))
                .isEqualTo(ConversationManager.TranscriptResult.IGNORED);
        assertThat(manager.acceptTranscript(transcript("missing", TranscriptType.FINAL, "final", 1)))
                .isEqualTo(ConversationManager.TranscriptResult.NO_SESSION);
        llmService.addResponse(LLMResponse.success("answer"));
        assertThat(manager.acceptTranscript(transcript("call-a", TranscriptType.FINAL, "final", 2)))
                .isEqualTo(ConversationManager.TranscriptResult.ACCEPTED);
        assertThat(manager.acceptTranscript(transcript("call-a", TranscriptType.FINAL, "final", 2)))
                .isEqualTo(ConversationManager.TranscriptResult.DUPLICATE);
    }

    @Test
    void nullAndWhitespaceTranscriptAreIgnored() {
        manager.startSession("call-a", ignored -> { });
        Transcript whitespace = mock(Transcript.class);
        when(whitespace.type()).thenReturn(TranscriptType.FINAL);
        when(whitespace.text()).thenReturn("   ");

        assertThat(manager.acceptTranscript(null)).isEqualTo(ConversationManager.TranscriptResult.IGNORED);
        assertThat(manager.acceptTranscript(whitespace)).isEqualTo(ConversationManager.TranscriptResult.IGNORED);
        assertThat(llmService.requests).isEmpty();
    }

    @Test
    void multipleTurnsAreSerializedAndIncludePriorContext() throws Exception {
        List<AssistantResponse> responses = new CopyOnWriteArrayList<>();
        CompletableFuture<LLMResponse> first = llmService.addPendingResponse();
        llmService.addResponse(LLMResponse.success("second answer"));
        manager.startSession("call-a", responses::add);

        manager.acceptTranscript(transcript("call-a", TranscriptType.FINAL, "first question", 1));
        manager.acceptTranscript(transcript("call-a", TranscriptType.FINAL, "second question", 2));
        await(() -> llmService.requests.size() == 1);
        assertThat(llmService.requests).hasSize(1);

        first.complete(LLMResponse.success("first answer"));
        await(() -> llmService.requests.size() == 2 && responses.size() == 2);

        assertThat(llmService.requests.get(1).messages())
                .extracting(LLMMessage::text)
                .containsExactly("first question", "first answer", "second question");
        assertThat(responses).extracting(AssistantResponse::text)
                .containsExactly("first answer", "second answer");
    }

    @Test
    void historyUsesConfiguredMessageAndCharacterBounds() throws Exception {
        properties.setMaxMessages(3);
        properties.setMaxContextCharacters(18);
        properties.setMaxMessageCharacters(7);
        manager.shutdown();
        manager = new ConversationManager(llmService, properties, new AgriculturalAssistantPrompt(properties));
        manager.startSession("call-a", ignored -> { });
        llmService.addResponse(LLMResponse.success("answer-one"));
        llmService.addResponse(LLMResponse.success("answer-two"));

        manager.acceptTranscript(transcript("call-a", TranscriptType.FINAL, "question-one-long", 1));
        await(() -> llmService.requests.size() == 1);
        manager.acceptTranscript(transcript("call-a", TranscriptType.FINAL, "question-two-long", 2));
        await(() -> llmService.requests.size() == 2);

        List<LLMMessage> history = manager.history("call-a");
        assertThat(history.size()).isLessThanOrEqualTo(3);
        assertThat(history.stream().mapToInt(message -> message.text().length()).sum()).isLessThanOrEqualTo(18);
        assertThat(history).allMatch(message -> message.text().length() <= 7);
    }

    @Test
    void providerFailureReturnsSafeFallbackWithoutBreakingNextTurn() throws Exception {
        List<AssistantResponse> responses = new CopyOnWriteArrayList<>();
        manager.startSession("call-a", responses::add);
        llmService.addResponse(LLMResponse.failure(LLMResponse.Status.TIMEOUT));
        llmService.addResponse(LLMResponse.success("recovered"));

        manager.acceptTranscript(transcript("call-a", TranscriptType.FINAL, "one", 1));
        manager.acceptTranscript(transcript("call-a", TranscriptType.FINAL, "two", 2));
        await(() -> responses.size() == 2);

        assertThat(responses.get(0).fallback()).isTrue();
        assertThat(responses.get(0).text()).isEqualTo(properties.getFallbackResponse());
        assertThat(responses.get(1).text()).isEqualTo("recovered");
    }

    @Test
    void sessionsAreIsolatedAndCanProgressConcurrently() throws Exception {
        List<AssistantResponse> responses = new CopyOnWriteArrayList<>();
        CompletableFuture<LLMResponse> first = llmService.addPendingResponse();
        CompletableFuture<LLMResponse> second = llmService.addPendingResponse();
        manager.startSession("call-a", responses::add);
        manager.startSession("call-b", responses::add);

        manager.acceptTranscript(transcript("call-a", TranscriptType.FINAL, "alpha", 1));
        await(() -> llmService.requests.size() == 1);
        manager.acceptTranscript(transcript("call-b", TranscriptType.FINAL, "beta", 1));
        await(() -> llmService.requests.size() == 2);
        first.complete(LLMResponse.success("answer-alpha"));
        second.complete(LLMResponse.success("answer-beta"));
        await(() -> responses.size() == 2);

        assertThat(llmService.requests).extracting(LLMRequest::conversationId)
                .containsExactlyInAnyOrder("call-a", "call-b");
        assertThat(manager.history("call-a")).extracting(LLMMessage::text).contains("alpha", "answer-alpha");
        assertThat(manager.history("call-b")).extracting(LLMMessage::text).contains("beta", "answer-beta");
    }

    @Test
    void closeIsIdempotentClearsStateAndSuppressesLateResponse() throws Exception {
        List<AssistantResponse> responses = new CopyOnWriteArrayList<>();
        CompletableFuture<LLMResponse> pending = llmService.addPendingResponse();
        manager.startSession("call-a", responses::add);
        manager.acceptTranscript(transcript("call-a", TranscriptType.FINAL, "question", 1));
        await(() -> llmService.requests.size() == 1);

        assertThat(manager.closeSession("call-a")).isEqualTo(ConversationManager.CloseResult.CLOSED);
        assertThat(manager.closeSession("call-a")).isEqualTo(ConversationManager.CloseResult.NOT_FOUND);
        assertThat(manager.activeSessionCount()).isZero();
        assertThat(manager.history("call-a")).isEmpty();
        pending.complete(LLMResponse.success("late answer"));
        Thread.sleep(50);
        assertThat(responses).isEmpty();
    }

    @Test
    void validatesStartsAndRejectsDuplicateSession() {
        assertThat(manager.startSession(null, ignored -> { })).isEqualTo(ConversationManager.StartResult.INVALID);
        assertThat(manager.startSession("call-a", ignored -> { })).isEqualTo(ConversationManager.StartResult.STARTED);
        assertThat(manager.startSession("call-a", ignored -> { })).isEqualTo(ConversationManager.StartResult.DUPLICATE);
        assertThat(manager.activeSessionCount()).isOne();
    }

    private Transcript transcript(String id, TranscriptType type, String text, long sequence) {
        return new Transcript(id, "call-sid", "stream-sid", text, type, Instant.now(), null, sequence);
    }

    private void await(Check check) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(2);
        while (!check.done() && System.nanoTime() < deadline) {
            Thread.sleep(10);
        }
        assertThat(check.done()).isTrue();
    }

    @FunctionalInterface
    private interface Check {
        boolean done();
    }

    private static final class ControlledLlmService implements LLMService {

        private final List<LLMRequest> requests = new CopyOnWriteArrayList<>();
        private final List<CompletableFuture<LLMResponse>> responses = new ArrayList<>();

        synchronized void addResponse(LLMResponse response) {
            responses.add(CompletableFuture.completedFuture(response));
        }

        synchronized CompletableFuture<LLMResponse> addPendingResponse() {
            CompletableFuture<LLMResponse> response = new CompletableFuture<>();
            responses.add(response);
            return response;
        }

        @Override
        public synchronized CompletableFuture<LLMResponse> generate(LLMRequest request) {
            requests.add(request);
            if (responses.isEmpty()) {
                return CompletableFuture.completedFuture(LLMResponse.failure(LLMResponse.Status.NETWORK_FAILURE));
            }
            return responses.removeFirst();
        }
    }
}
