package com.agri.voice.ai.llm.gemini;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;

import org.springframework.stereotype.Component;

@Component
final class JdkGeminiLlmTransport implements GeminiLlmTransport {

    private final HttpClient httpClient;

    JdkGeminiLlmTransport() {
        this(HttpClient.newBuilder().build());
    }

    JdkGeminiLlmTransport(HttpClient httpClient) {
        this.httpClient = Objects.requireNonNull(httpClient);
    }

    @Override
    public CompletableFuture<TransportResponse> postJson(
            URI endpoint,
            String apiKey,
            String json,
            Duration timeout,
            int maxResponseBodyBytes) {
        HttpRequest request = HttpRequest.newBuilder(endpoint)
                .timeout(timeout)
                .header("Content-Type", "application/json")
                .header("x-goog-api-key", apiKey)
                .POST(HttpRequest.BodyPublishers.ofString(json, StandardCharsets.UTF_8))
                .build();

        return httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofInputStream())
                .thenApply(response -> readBounded(response, maxResponseBodyBytes));
    }

    private TransportResponse readBounded(
            HttpResponse<InputStream> response,
            int maxResponseBodyBytes) {
        try (InputStream body = response.body()) {
            byte[] bytes = body.readNBytes(maxResponseBodyBytes + 1);
            boolean oversized = bytes.length > maxResponseBodyBytes;
            if (oversized) {
                bytes = new byte[0];
            }
            return new TransportResponse(response.statusCode(), bytes, oversized);
        } catch (IOException exception) {
            throw new CompletionException(exception);
        }
    }
}
