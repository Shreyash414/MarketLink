package com.agri.voice.ai.llm.gemini;

import java.time.Duration;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "gemini.llm")
public class GeminiLlmProperties {

    static final String DEFAULT_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions";

    private boolean enabled = true;
    private String apiKey = "";
    private String model = "gemini-3.5-flash-lite";
    private String endpoint = DEFAULT_ENDPOINT;
    private Duration timeout = Duration.ofSeconds(20);
    private int maxOutputTokens = 96;
    private int maxInputCharacters = 16_000;
    private int maxResponseCharacters = 2_000;
    private int maxResponseBodyBytes = 262_144;
    private String thinkingLevel = "minimal";

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public String getApiKey() {
        return apiKey;
    }

    public void setApiKey(String apiKey) {
        this.apiKey = apiKey;
    }

    public String getModel() {
        return model;
    }

    public void setModel(String model) {
        this.model = model;
    }

    public String getEndpoint() {
        return endpoint;
    }

    public void setEndpoint(String endpoint) {
        this.endpoint = endpoint;
    }

    public Duration getTimeout() {
        return timeout;
    }

    public void setTimeout(Duration timeout) {
        this.timeout = timeout;
    }

    public int getMaxOutputTokens() {
        return maxOutputTokens;
    }

    public void setMaxOutputTokens(int maxOutputTokens) {
        this.maxOutputTokens = maxOutputTokens;
    }

    public int getMaxInputCharacters() {
        return maxInputCharacters;
    }

    public void setMaxInputCharacters(int maxInputCharacters) {
        this.maxInputCharacters = maxInputCharacters;
    }

    public int getMaxResponseCharacters() {
        return maxResponseCharacters;
    }

    public void setMaxResponseCharacters(int maxResponseCharacters) {
        this.maxResponseCharacters = maxResponseCharacters;
    }

    public int getMaxResponseBodyBytes() {
        return maxResponseBodyBytes;
    }

    public void setMaxResponseBodyBytes(int maxResponseBodyBytes) {
        this.maxResponseBodyBytes = maxResponseBodyBytes;
    }

    public String getThinkingLevel() {
        return thinkingLevel;
    }

    public void setThinkingLevel(String thinkingLevel) {
        this.thinkingLevel = thinkingLevel;
    }

}
