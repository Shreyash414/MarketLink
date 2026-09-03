package com.agri.voice.voice;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.nio.ByteBuffer;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;

@SpringBootTest(
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {
                "spring.autoconfigure.exclude="
                        + "org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration,"
                        + "org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration",
                "gemini.stt.enabled=false"
        })
class VoiceWebSocketIntegrationTest {

    @LocalServerPort
    private int port;

    @Autowired
    private VoiceWebSocketHandler handler;

    @Test
    void mediaEndpointAcceptsRepresentativeExotelLifecycle() throws Exception {
        CountDownLatch opened = new CountDownLatch(1);
        CountDownLatch closed = new CountDownLatch(1);
        WebSocket.Listener listener = new WebSocket.Listener() {
            @Override
            public void onOpen(WebSocket webSocket) {
                opened.countDown();
                webSocket.request(1);
            }

            @Override
            public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
                webSocket.request(1);
                return null;
            }

            @Override
            public CompletionStage<?> onBinary(WebSocket webSocket, ByteBuffer data, boolean last) {
                webSocket.request(1);
                return null;
            }

            @Override
            public CompletionStage<?> onClose(WebSocket webSocket, int statusCode, String reason) {
                closed.countDown();
                return null;
            }
        };

        WebSocket webSocket = HttpClient.newHttpClient()
                .newWebSocketBuilder()
                .buildAsync(URI.create("ws://localhost:" + port + "/media"), listener)
                .get(5, TimeUnit.SECONDS);

        assertThat(opened.await(5, TimeUnit.SECONDS)).isTrue();
        webSocket.sendText(ExotelTestMessages.connected(), true).join();
        webSocket.sendText(ExotelTestMessages.start(16_000), true).join();
        webSocket.sendText(
                ExotelTestMessages.media(2, 1, 100, ExotelTestMessages.pcmFrame()), true).join();
        webSocket.sendText(ExotelTestMessages.stop(), true).join();

        assertThat(closed.await(5, TimeUnit.SECONDS)).isTrue();
        assertThat(waitForSessionCleanup()).isTrue();
    }

    private boolean waitForSessionCleanup() throws InterruptedException {
        for (int attempt = 0; attempt < 20; attempt++) {
            if (handler.activeSessionCount() == 0) {
                return true;
            }
            Thread.sleep(25);
        }
        return false;
    }
}
