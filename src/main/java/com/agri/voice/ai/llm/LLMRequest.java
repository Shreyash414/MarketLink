package com.agri.voice.ai.llm;

import java.util.List;

public record LLMRequest(
        String conversationId,
        String systemInstruction,
        List<LLMMessage> messages) {

    public LLMRequest {
        requireText(conversationId, "conversationId");
        requireText(systemInstruction, "systemInstruction");
        if (messages == null || messages.isEmpty()) {
            throw new IllegalArgumentException("messages must not be empty");
        }
        messages = List.copyOf(messages);
        if (messages.stream().anyMatch(message -> message == null)) {
            throw new IllegalArgumentException("messages must not contain null values");
        }
    }

    public long inputCharacterCount() {
        return systemInstruction.length()
                + messages.stream().mapToLong(message -> message.text().length()).sum();
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
    }
}
