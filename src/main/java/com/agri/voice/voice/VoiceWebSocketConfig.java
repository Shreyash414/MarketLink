package com.agri.voice.voice;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.server.standard.ServletServerContainerFactoryBean;

@Configuration
@EnableWebSocket
public class VoiceWebSocketConfig implements WebSocketConfigurer {

    private final VoiceWebSocketHandler voiceWebSocketHandler;
    private final String webSocketPath;
    private final int maxTextMessageSize;

    public VoiceWebSocketConfig(
            VoiceWebSocketHandler voiceWebSocketHandler,
            @Value("${voice.websocket.path:/media}") String webSocketPath,
            @Value("${voice.websocket.max-text-message-size:150000}") int maxTextMessageSize) {
        this.voiceWebSocketHandler = voiceWebSocketHandler;
        if (webSocketPath == null || webSocketPath.isBlank() || !webSocketPath.startsWith("/")) {
            throw new IllegalArgumentException("voice.websocket.path must start with '/'");
        }
        this.webSocketPath = webSocketPath;
        this.maxTextMessageSize = maxTextMessageSize;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(voiceWebSocketHandler, webSocketPath);
    }

    @Bean
    ServletServerContainerFactoryBean webSocketContainer() {
        ServletServerContainerFactoryBean container = new ServletServerContainerFactoryBean();
        container.setMaxTextMessageBufferSize(maxTextMessageSize);
        return container;
    }
}
