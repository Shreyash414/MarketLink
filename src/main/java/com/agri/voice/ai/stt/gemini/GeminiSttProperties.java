package com.agri.voice.ai.stt.gemini;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "gemini.stt")
public class GeminiSttProperties {

    private boolean enabled = true;
    private String apiKey = "";
    private String model = "gemini-3.5-transcribe-live";
    private String endpoint = "wss://generativelanguage.googleapis.com/ws/"
            + "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent";
    private int sampleRate = 16_000;
    private String mode = "VERBATIM";
    private List<String> languageCodes = new ArrayList<>();
    private List<String> customVocabulary = new ArrayList<>();
    private int queueCapacity = 20;
    private Duration connectTimeout = Duration.ofSeconds(10);
    private Duration setupTimeout = Duration.ofSeconds(10);
    private Duration sendTimeout = Duration.ofSeconds(5);

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

    public int getSampleRate() {
        return sampleRate;
    }

    public void setSampleRate(int sampleRate) {
        this.sampleRate = sampleRate;
    }

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

    public List<String> getLanguageCodes() {
        return languageCodes;
    }

    public void setLanguageCodes(List<String> languageCodes) {
        this.languageCodes = languageCodes == null ? new ArrayList<>() : new ArrayList<>(languageCodes);
    }

    public List<String> getCustomVocabulary() {
        return customVocabulary;
    }

    public void setCustomVocabulary(List<String> customVocabulary) {
        this.customVocabulary = customVocabulary == null
                ? new ArrayList<>()
                : new ArrayList<>(customVocabulary);
    }

    public int getQueueCapacity() {
        return queueCapacity;
    }

    public void setQueueCapacity(int queueCapacity) {
        this.queueCapacity = queueCapacity;
    }

    public Duration getConnectTimeout() {
        return connectTimeout;
    }

    public void setConnectTimeout(Duration connectTimeout) {
        this.connectTimeout = connectTimeout;
    }

    public Duration getSetupTimeout() {
        return setupTimeout;
    }

    public void setSetupTimeout(Duration setupTimeout) {
        this.setupTimeout = setupTimeout;
    }

    public Duration getSendTimeout() {
        return sendTimeout;
    }

    public void setSendTimeout(Duration sendTimeout) {
        this.sendTimeout = sendTimeout;
    }
}
