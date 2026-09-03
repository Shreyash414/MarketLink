package com.agri.voice.ai.llm.gemini;

import java.net.URI;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

interface GeminiLlmTransport {

    CompletableFuture<TransportResponse> postJson(
            URI endpoint,
            String apiKey,
            String json,
            Duration timeout,
            int maxResponseBodyBytes);

    record TransportResponse(int statusCode, byte[] body, boolean oversized) {

        public TransportResponse {
            body = body == null ? new byte[0] : body.clone();
        }

        @Override
        public byte[] body() {
            return body.clone();
        }
    }
}
