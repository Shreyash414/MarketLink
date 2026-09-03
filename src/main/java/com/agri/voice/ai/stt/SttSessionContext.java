package com.agri.voice.ai.stt;

public record SttSessionContext(
        String transportSessionId,
        String callSid,
        String streamSid,
        int inputSampleRate,
        int channels,
        int bitsPerSample) {

    public SttSessionContext {
        requireText(transportSessionId, "transportSessionId");
        requireText(callSid, "callSid");
        requireText(streamSid, "streamSid");
        if (inputSampleRate <= 0 || channels <= 0 || bitsPerSample <= 0) {
            throw new IllegalArgumentException("audio format values must be positive");
        }
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
    }
}
