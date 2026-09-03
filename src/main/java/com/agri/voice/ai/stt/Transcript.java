package com.agri.voice.ai.stt;

import java.time.Instant;
import java.util.Objects;

public record Transcript(
        String transportSessionId,
        String callSid,
        String streamSid,
        String text,
        TranscriptType type,
        Instant receivedAt,
        String detectedLanguage,
        long sequenceNumber) {

    public Transcript {
        requireText(transportSessionId, "transportSessionId");
        requireText(callSid, "callSid");
        requireText(streamSid, "streamSid");
        requireText(text, "text");
        Objects.requireNonNull(type, "type must not be null");
        Objects.requireNonNull(receivedAt, "receivedAt must not be null");
        if (sequenceNumber < 0) {
            throw new IllegalArgumentException("sequenceNumber must not be negative");
        }
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
    }
}
