package com.agri.voice.ai.stt.gemini;

import java.net.http.HttpClient;

import org.springframework.stereotype.Component;

@Component
public final class JdkGeminiLiveTransportFactory implements GeminiLiveTransportFactory {

    private final HttpClient httpClient = HttpClient.newBuilder().build();

    @Override
    public GeminiLiveTransport create() {
        return new JdkGeminiLiveTransport(httpClient);
    }
}
