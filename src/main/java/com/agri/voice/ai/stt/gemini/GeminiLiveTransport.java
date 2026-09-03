package com.agri.voice.ai.stt.gemini;

import java.net.URI;
import java.util.concurrent.CompletableFuture;

public interface GeminiLiveTransport {

    CompletableFuture<Void> connect(URI endpoint, Listener listener);

    CompletableFuture<Void> sendText(String message);

    CompletableFuture<Void> close();

    interface Listener {

        void onText(String message);

        void onClosed(int statusCode, String reason);

        void onError(Throwable error);
    }
}
