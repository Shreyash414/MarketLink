package com.agri.voice.ai.llm.gemini;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;

import com.agri.voice.ai.llm.LLMMessage;
import com.agri.voice.ai.llm.LLMRequest;
import com.agri.voice.ai.llm.LLMResponse;
import com.agri.voice.ai.llm.LLMRole;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;

class GeminiLLMServiceTest {

    private static final String API_KEY = "test-key-must-never-be-logged";
    private static final String USER_TEXT = "मेरे खेत का निजी सवाल";

    private final ObjectMapper objectMapper = new ObjectMapper();
    private GeminiLlmProperties properties;
    private RecordingTransport transport;
    private GeminiLLMService service;
    private Logger logger;
    private ListAppender<ILoggingEvent> appender;

    @BeforeEach
    void setUp() {
        properties = new GeminiLlmProperties();
        properties.setApiKey(API_KEY);
        transport = new RecordingTransport();
        service = new GeminiLLMService(
                properties,
                transport,
                new GeminiInteractionResponseParser(objectMapper),
                objectMapper);
        logger = (Logger) LoggerFactory.getLogger(GeminiLLMService.class);
        appender = new ListAppender<>();
        appender.start();
        logger.addAppender(appender);
    }

    @AfterEach
    void tearDown() {
        logger.detachAppender(appender);
        appender.stop();
    }

    @Test
    void sendsOfficialStatelessInteractionsRequestAndParsesResponse() throws Exception {
        transport.response = completed(200, """
                {"steps":[{"type":"model_output","content":[{"type":"text","text":"गेहूं को सूखा रखें।"}]}]}
                """);

        LLMResponse response = service.generate(request()).get(2, TimeUnit.SECONDS);

        assertThat(response.status()).isEqualTo(LLMResponse.Status.SUCCESS);
        assertThat(response.text()).isEqualTo("गेहूं को सूखा रखें।");
        assertThat(transport.endpoint).isEqualTo(URI.create(GeminiLlmProperties.DEFAULT_ENDPOINT));
        assertThat(transport.apiKey).isEqualTo(API_KEY);
        JsonNode request = objectMapper.readTree(transport.json);
        assertThat(request.path("model").asText()).isEqualTo("gemini-3.5-flash-lite");
        assertThat(request.path("system_instruction").asText()).isEqualTo("Be concise");
        assertThat(request.path("store").asBoolean()).isFalse();
        assertThat(request.path("input").get(0).path("type").asText()).isEqualTo("user_input");
        assertThat(request.path("input").get(1).path("type").asText()).isEqualTo("model_output");
        assertThat(request.path("input").get(2).path("type").asText()).isEqualTo("user_input");
        assertThat(request.path("generation_config").path("max_output_tokens").asInt()).isEqualTo(96);
        assertThat(request.path("generation_config").path("thinking_level").asText()).isEqualTo("minimal");
    }

    @Test
    void disabledMissingCredentialAndOversizedInputFailWithoutTransportCall() throws Exception {
        properties.setEnabled(false);
        assertThat(service.generate(request()).get().status()).isEqualTo(LLMResponse.Status.DISABLED);
        properties.setEnabled(true);
        properties.setApiKey(" ");
        assertThat(service.generate(request()).get().status()).isEqualTo(LLMResponse.Status.MISSING_CREDENTIAL);
        properties.setApiKey(API_KEY);
        properties.setMaxInputCharacters(2);
        assertThat(service.generate(request()).get().status()).isEqualTo(LLMResponse.Status.INVALID_REQUEST);
        assertThat(transport.calls).isZero();
    }

    @Test
    void rejectsUnsafeOrInvalidConfiguration() throws Exception {
        properties.setEndpoint("https://user:password@example.test/v1?key=secret");
        assertThat(service.generate(request()).get().status()).isEqualTo(LLMResponse.Status.INVALID_CONFIGURATION);
        properties.setEndpoint("http://example.test/v1");
        assertThat(service.generate(request()).get().status()).isEqualTo(LLMResponse.Status.INVALID_CONFIGURATION);
        properties.setEndpoint(GeminiLlmProperties.DEFAULT_ENDPOINT);
        properties.setModel("bad/model?key=secret");
        assertThat(service.generate(request()).get().status()).isEqualTo(LLMResponse.Status.INVALID_CONFIGURATION);
        properties.setModel("gemini-3.5-flash-lite");
        properties.setThinkingLevel("unsupported");
        assertThat(service.generate(request()).get().status()).isEqualTo(LLMResponse.Status.INVALID_CONFIGURATION);
        assertThat(transport.calls).isZero();
    }

    @Test
    void mapsProviderAndParsingFailuresToTypedResults() throws Exception {
        assertStatus(401, "credential detail", LLMResponse.Status.AUTHENTICATION_FAILURE);
        assertStatus(403, "credential detail", LLMResponse.Status.AUTHENTICATION_FAILURE);
        assertStatus(429, "quota detail", LLMResponse.Status.RATE_LIMITED);
        assertStatus(500, "server detail", LLMResponse.Status.PROVIDER_SERVER_ERROR);
        assertStatus(400, "request detail", LLMResponse.Status.PROVIDER_CLIENT_ERROR);
        assertStatus(200, "not-json", LLMResponse.Status.MALFORMED_RESPONSE);
        assertStatus(200, "{\"steps\":[]}", LLMResponse.Status.EMPTY_RESPONSE);
    }

    @Test
    void handlesNetworkTimeoutAndBoundedResponses() throws Exception {
        transport.response = CompletableFuture.failedFuture(new IllegalStateException("network secret"));
        assertThat(service.generate(request()).get().status()).isEqualTo(LLMResponse.Status.NETWORK_FAILURE);

        transport.response = new CompletableFuture<>();
        properties.setTimeout(Duration.ofMillis(25));
        assertThat(service.generate(request()).get(1, TimeUnit.SECONDS).status()).isEqualTo(LLMResponse.Status.TIMEOUT);

        properties.setTimeout(Duration.ofSeconds(1));
        transport.response = CompletableFuture.completedFuture(
                new GeminiLlmTransport.TransportResponse(200, new byte[0], true));
        assertThat(service.generate(request()).get().status()).isEqualTo(LLMResponse.Status.RESPONSE_TOO_LARGE);

        properties.setMaxResponseCharacters(3);
        transport.response = completed(200,
                "{\"steps\":[{\"type\":\"model_output\",\"content\":[{\"type\":\"text\",\"text\":\"long\"}]}]}");
        assertThat(service.generate(request()).get().status()).isEqualTo(LLMResponse.Status.RESPONSE_TOO_LARGE);
    }

    @Test
    void logsOnlySafeMetadata() throws Exception {
        transport.response = completed(401, "body-with-provider-secret");

        service.generate(request()).get();

        String logs = appender.list.stream()
                .map(event -> event.getFormattedMessage() + " " + event.getKeyValuePairs())
                .reduce("", (left, right) -> left + right);
        assertThat(logs).contains("LLM request completed", "AUTHENTICATION_FAILURE", "conversation-1");
        assertThat(logs).doesNotContain(API_KEY, USER_TEXT, "body-with-provider-secret", "Authorization");
    }

    private void assertStatus(int status, String body, LLMResponse.Status expected) throws Exception {
        transport.response = completed(status, body);
        assertThat(service.generate(request()).get().status()).isEqualTo(expected);
    }

    private LLMRequest request() {
        return new LLMRequest("conversation-1", "Be concise", List.of(
                new LLMMessage(LLMRole.USER, "पहला सवाल"),
                new LLMMessage(LLMRole.ASSISTANT, "पहला जवाब"),
                new LLMMessage(LLMRole.USER, USER_TEXT)));
    }

    private CompletableFuture<GeminiLlmTransport.TransportResponse> completed(int status, String body) {
        return CompletableFuture.completedFuture(new GeminiLlmTransport.TransportResponse(
                status, body.getBytes(StandardCharsets.UTF_8), false));
    }

    private static final class RecordingTransport implements GeminiLlmTransport {

        private CompletableFuture<TransportResponse> response = new CompletableFuture<>();
        private URI endpoint;
        private String apiKey;
        private String json;
        private int calls;

        @Override
        public CompletableFuture<TransportResponse> postJson(
                URI endpoint,
                String apiKey,
                String json,
                Duration timeout,
                int maxResponseBodyBytes) {
            calls++;
            this.endpoint = endpoint;
            this.apiKey = apiKey;
            this.json = json;
            return response;
        }
    }
}
