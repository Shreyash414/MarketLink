package com.agri.voice.ai.stt.gemini;

import java.io.ByteArrayOutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.atomic.AtomicBoolean;

final class JdkGeminiLiveTransport implements GeminiLiveTransport {

    private static final int MAX_RESPONSE_CHARACTERS = 64_000;
    private static final int MAX_RESPONSE_BYTES = MAX_RESPONSE_CHARACTERS * 4;

    private final HttpClient httpClient;
    private final AtomicBoolean closed = new AtomicBoolean();
    private volatile WebSocket webSocket;

    JdkGeminiLiveTransport(HttpClient httpClient) {
        this.httpClient = Objects.requireNonNull(httpClient);
    }

    @Override
    public CompletableFuture<Void> connect(URI endpoint, Listener listener) {
        Objects.requireNonNull(endpoint);
        Objects.requireNonNull(listener);
        if (closed.get()) {
            return CompletableFuture.failedFuture(new IllegalStateException("transport is closed"));
        }

        return httpClient.newWebSocketBuilder()
                .buildAsync(endpoint, new ProviderListener(listener))
                .thenAccept(socket -> webSocket = socket);
    }

    final class ProviderListener implements WebSocket.Listener {

        private final Listener listener;
        private final StringBuilder textBuffer = new StringBuilder();
        private final ByteArrayOutputStream binaryBuffer = new ByteArrayOutputStream();
        private boolean discardingText;
        private boolean discardingBinary;

        ProviderListener(Listener listener) {
            this.listener = Objects.requireNonNull(listener);
        }

        @Override
        public void onOpen(WebSocket socket) {
            webSocket = socket;
            socket.request(1);
        }

        @Override
        public CompletionStage<?> onText(WebSocket socket, CharSequence data, boolean last) {
            synchronized (textBuffer) {
                if (!discardingText && textBuffer.length() + data.length() > MAX_RESPONSE_CHARACTERS) {
                    textBuffer.setLength(0);
                    discardingText = true;
                    listener.onError(new IllegalStateException(
                            "provider text response exceeded safe limit"));
                } else if (!discardingText) {
                    textBuffer.append(data);
                    if (last) {
                        String message = textBuffer.toString();
                        textBuffer.setLength(0);
                        listener.onText(message);
                    }
                }
                if (last) {
                    discardingText = false;
                }
            }
            socket.request(1);
            return CompletableFuture.completedFuture(null);
        }

        @Override
        public CompletionStage<?> onBinary(WebSocket socket, ByteBuffer data, boolean last) {
            synchronized (binaryBuffer) {
                int bytes = data.remaining();
                if (!discardingBinary && binaryBuffer.size() + bytes > MAX_RESPONSE_BYTES) {
                    binaryBuffer.reset();
                    discardingBinary = true;
                    listener.onError(new IllegalStateException(
                            "provider binary response exceeded safe limit"));
                } else if (!discardingBinary) {
                    byte[] fragment = new byte[bytes];
                    data.get(fragment);
                    binaryBuffer.writeBytes(fragment);
                    if (last) {
                        decodeBinaryMessage();
                    }
                }
                if (last) {
                    binaryBuffer.reset();
                    discardingBinary = false;
                }
            }
            socket.request(1);
            return CompletableFuture.completedFuture(null);
        }

        private void decodeBinaryMessage() {
            try {
                String message = StandardCharsets.UTF_8.newDecoder()
                        .onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT)
                        .decode(ByteBuffer.wrap(binaryBuffer.toByteArray()))
                        .toString();
                listener.onText(message);
            } catch (CharacterCodingException exception) {
                listener.onError(new IllegalArgumentException(
                        "provider binary response was not valid UTF-8", exception));
            }
        }

        @Override
        public CompletionStage<?> onClose(WebSocket socket, int statusCode, String reason) {
            closed.set(true);
            listener.onClosed(statusCode, reason);
            return CompletableFuture.completedFuture(null);
        }

        @Override
        public void onError(WebSocket socket, Throwable error) {
            closed.set(true);
            listener.onError(error);
        }
    }

    @Override
    public CompletableFuture<Void> sendText(String message) {
        WebSocket socket = webSocket;
        if (socket == null || closed.get()) {
            return CompletableFuture.failedFuture(new IllegalStateException("transport is not open"));
        }
        return socket.sendText(message, true).thenApply(ignored -> null);
    }

    @Override
    public CompletableFuture<Void> close() {
        WebSocket socket = webSocket;
        if (!closed.compareAndSet(false, true) || socket == null) {
            return CompletableFuture.completedFuture(null);
        }
        return socket.sendClose(WebSocket.NORMAL_CLOSURE, "complete").thenApply(ignored -> null);
    }
}
