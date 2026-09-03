package com.agri.voice.ai.llm.gemini;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.sun.net.httpserver.HttpServer;

class JdkGeminiLlmTransportTest {

    private HttpServer server;
    private URI endpoint;
    private AtomicReference<String> receivedKey;
    private AtomicReference<String> receivedBody;

    @BeforeEach
    void setUp() throws IOException {
        receivedKey = new AtomicReference<>();
        receivedBody = new AtomicReference<>();
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/interactions", exchange -> {
            receivedKey.set(exchange.getRequestHeaders().getFirst("x-goog-api-key"));
            receivedBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            byte[] response = "0123456789".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        server.start();
        endpoint = URI.create("http://127.0.0.1:" + server.getAddress().getPort() + "/interactions");
    }

    @AfterEach
    void tearDown() {
        server.stop(0);
    }

    @Test
    void sendsApiKeyOnlyAsHeaderAndReadsResponse() throws Exception {
        JdkGeminiLlmTransport transport = new JdkGeminiLlmTransport(HttpClient.newHttpClient());

        GeminiLlmTransport.TransportResponse response = transport.postJson(
                        endpoint, "private-test-key", "{\"store\":false}", Duration.ofSeconds(2), 100)
                .get(2, TimeUnit.SECONDS);

        assertThat(response.statusCode()).isEqualTo(200);
        assertThat(new String(response.body(), StandardCharsets.UTF_8)).isEqualTo("0123456789");
        assertThat(receivedKey).hasValue("private-test-key");
        assertThat(receivedBody).hasValue("{\"store\":false}");
        assertThat(endpoint.toString()).doesNotContain("private-test-key");
    }

    @Test
    void discardsResponseWhenConfiguredBodyLimitIsExceeded() throws Exception {
        JdkGeminiLlmTransport transport = new JdkGeminiLlmTransport(HttpClient.newHttpClient());

        GeminiLlmTransport.TransportResponse response = transport.postJson(
                        endpoint, "private-test-key", "{}", Duration.ofSeconds(2), 5)
                .get(2, TimeUnit.SECONDS);

        assertThat(response.oversized()).isTrue();
        assertThat(response.body()).isEmpty();
    }
}
