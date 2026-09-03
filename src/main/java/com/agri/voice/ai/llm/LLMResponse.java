package com.agri.voice.ai.llm;

public record LLMResponse(Status status, String text, Integer providerStatus) {

    public LLMResponse {
        if (status == null) {
            throw new IllegalArgumentException("status must not be null");
        }
        if (status == Status.SUCCESS && (text == null || text.isBlank())) {
            throw new IllegalArgumentException("successful response text must not be blank");
        }
        text = text == null ? null : text.trim();
    }

    public static LLMResponse success(String text) {
        return new LLMResponse(Status.SUCCESS, text, 200);
    }

    public static LLMResponse failure(Status status) {
        return new LLMResponse(status, null, null);
    }

    public static LLMResponse failure(Status status, Integer providerStatus) {
        return new LLMResponse(status, null, providerStatus);
    }

    public boolean successful() {
        return status == Status.SUCCESS;
    }

    public enum Status {
        SUCCESS,
        DISABLED,
        MISSING_CREDENTIAL,
        INVALID_CONFIGURATION,
        INVALID_REQUEST,
        TIMEOUT,
        NETWORK_FAILURE,
        AUTHENTICATION_FAILURE,
        RATE_LIMITED,
        PROVIDER_CLIENT_ERROR,
        PROVIDER_SERVER_ERROR,
        MALFORMED_RESPONSE,
        EMPTY_RESPONSE,
        RESPONSE_TOO_LARGE,
        INTERRUPTED
    }
}
