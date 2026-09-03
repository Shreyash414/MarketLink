package com.agri.voice.ai.llm.gemini;

import java.net.URI;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import com.agri.voice.ai.llm.LLMMessage;
import com.agri.voice.ai.llm.LLMRequest;
import com.agri.voice.ai.llm.LLMResponse;
import com.agri.voice.ai.llm.LLMResponse.Status;
import com.agri.voice.ai.llm.LLMRole;
import com.agri.voice.ai.llm.LLMService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

@Service
public final class GeminiLLMService implements LLMService {

    private static final Logger log = LoggerFactory.getLogger(GeminiLLMService.class);
    private static final Pattern MODEL_NAME = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._-]{0,127}");
    private static final Pattern THINKING_LEVEL = Pattern.compile("minimal|low|medium|high");

    private final GeminiLlmProperties properties;
    private final GeminiLlmTransport transport;
    private final GeminiInteractionResponseParser responseParser;
    private final ObjectMapper objectMapper;

    GeminiLLMService(
            GeminiLlmProperties properties,
            GeminiLlmTransport transport,
            GeminiInteractionResponseParser responseParser,
            ObjectMapper objectMapper) {
        this.properties = Objects.requireNonNull(properties);
        this.transport = Objects.requireNonNull(transport);
        this.responseParser = Objects.requireNonNull(responseParser);
        this.objectMapper = Objects.requireNonNull(objectMapper);
    }

    @Override
    public CompletableFuture<LLMResponse> generate(LLMRequest request) {
        if (!properties.isEnabled()) {
            return CompletableFuture.completedFuture(LLMResponse.failure(Status.DISABLED));
        }
        if (!hasText(properties.getApiKey())) {
            return CompletableFuture.completedFuture(LLMResponse.failure(Status.MISSING_CREDENTIAL));
        }
        if (!validConfiguration()) {
            return CompletableFuture.completedFuture(LLMResponse.failure(Status.INVALID_CONFIGURATION));
        }
        if (request == null || request.inputCharacterCount() > properties.getMaxInputCharacters()) {
            return CompletableFuture.completedFuture(LLMResponse.failure(Status.INVALID_REQUEST));
        }

        final String json;
        try {
            json = requestJson(request);
        } catch (JsonProcessingException exception) {
            return CompletableFuture.completedFuture(LLMResponse.failure(Status.INVALID_REQUEST));
        }

        long startedNanos = System.nanoTime();
        CompletableFuture<LLMResponse> result = transport.postJson(
                        URI.create(properties.getEndpoint()),
                        properties.getApiKey(),
                        json,
                        properties.getTimeout(),
                        properties.getMaxResponseBodyBytes())
                .orTimeout(properties.getTimeout().toMillis(), TimeUnit.MILLISECONDS)
                .handle((response, error) -> error == null
                        ? handleResponse(response)
                        : handleFailure(error));

        return result.whenComplete((response, error) -> {
            long latencyMillis = Duration.ofNanos(System.nanoTime() - startedNanos).toMillis();
            Status status = response == null ? Status.NETWORK_FAILURE : response.status();
            Integer providerStatus = response == null ? null : response.providerStatus();
            log.atInfo()
                    .addKeyValue("conversationId", request.conversationId())
                    .addKeyValue("provider", "gemini")
                    .addKeyValue("status", status)
                    .addKeyValue("providerStatus", providerStatus)
                    .addKeyValue("llmLatencyMs", latencyMillis)
                    .log("LLM request completed conversationId={} provider=gemini status={} providerStatus={} llmLatencyMs={}",
                            request.conversationId(), status, providerStatus, latencyMillis);
        });
    }

    private LLMResponse handleResponse(GeminiLlmTransport.TransportResponse response) {
        int statusCode = response.statusCode();
        if (statusCode == 401 || statusCode == 403) {
            return LLMResponse.failure(Status.AUTHENTICATION_FAILURE, statusCode);
        }
        if (statusCode == 429) {
            return LLMResponse.failure(Status.RATE_LIMITED, statusCode);
        }
        if (statusCode >= 500) {
            return LLMResponse.failure(Status.PROVIDER_SERVER_ERROR, statusCode);
        }
        if (statusCode < 200 || statusCode >= 300) {
            return LLMResponse.failure(Status.PROVIDER_CLIENT_ERROR, statusCode);
        }
        if (response.oversized()) {
            return LLMResponse.failure(Status.RESPONSE_TOO_LARGE, statusCode);
        }

        GeminiInteractionResponseParser.ParseResult parsed = responseParser.parse(response.body());
        if (parsed.status() == GeminiInteractionResponseParser.ParseResult.Status.MALFORMED) {
            return LLMResponse.failure(Status.MALFORMED_RESPONSE, statusCode);
        }
        if (parsed.status() == GeminiInteractionResponseParser.ParseResult.Status.EMPTY) {
            return LLMResponse.failure(Status.EMPTY_RESPONSE, statusCode);
        }
        if (parsed.text().length() > properties.getMaxResponseCharacters()) {
            return LLMResponse.failure(Status.RESPONSE_TOO_LARGE, statusCode);
        }
        return new LLMResponse(Status.SUCCESS, parsed.text(), statusCode);
    }

    private LLMResponse handleFailure(Throwable error) {
        Throwable cause = unwrap(error);
        if (cause instanceof TimeoutException || cause instanceof HttpTimeoutException) {
            return LLMResponse.failure(Status.TIMEOUT);
        }
        if (cause instanceof InterruptedException) {
            Thread.currentThread().interrupt();
            return LLMResponse.failure(Status.INTERRUPTED);
        }
        return LLMResponse.failure(Status.NETWORK_FAILURE);
    }

    private Throwable unwrap(Throwable error) {
        Throwable current = error;
        while ((current instanceof CompletionException || current instanceof java.util.concurrent.ExecutionException)
                && current.getCause() != null) {
            current = current.getCause();
        }
        return current;
    }

    private String requestJson(LLMRequest request) throws JsonProcessingException {
        List<Map<String, Object>> input = request.messages().stream()
                .map(this::interactionStep)
                .toList();
        Map<String, Object> generationConfig = new LinkedHashMap<>();
        generationConfig.put("max_output_tokens", properties.getMaxOutputTokens());
        generationConfig.put("thinking_level", properties.getThinkingLevel().trim());

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", properties.getModel().trim());
        body.put("system_instruction", request.systemInstruction());
        body.put("input", input);
        body.put("store", false);
        body.put("generation_config", generationConfig);
        return objectMapper.writeValueAsString(body);
    }

    private Map<String, Object> interactionStep(LLMMessage message) {
        String type = message.role() == LLMRole.USER ? "user_input" : "model_output";
        return Map.of(
                "type", type,
                "content", List.of(Map.of("type", "text", "text", message.text())));
    }

    private boolean validConfiguration() {
        if (!hasText(properties.getModel())
                || !MODEL_NAME.matcher(properties.getModel().trim()).matches()
                || properties.getTimeout() == null
                || properties.getTimeout().isZero()
                || properties.getTimeout().isNegative()
                || properties.getMaxOutputTokens() <= 0
                || properties.getMaxInputCharacters() <= 0
                || properties.getMaxResponseCharacters() <= 0
                || properties.getMaxResponseBodyBytes() <= 0
                || !hasText(properties.getThinkingLevel())
                || !THINKING_LEVEL.matcher(properties.getThinkingLevel().trim()).matches()) {
            return false;
        }
        try {
            URI endpoint = URI.create(properties.getEndpoint());
            return "https".equalsIgnoreCase(endpoint.getScheme())
                    && hasText(endpoint.getHost())
                    && endpoint.getRawUserInfo() == null
                    && endpoint.getRawQuery() == null;
        } catch (IllegalArgumentException exception) {
            return false;
        }
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
