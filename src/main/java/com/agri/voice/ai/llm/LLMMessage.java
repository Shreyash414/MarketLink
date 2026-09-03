package com.agri.voice.ai.llm;

import java.util.Objects;

public record LLMMessage(LLMRole role, String text) {

    public LLMMessage {
        Objects.requireNonNull(role, "role must not be null");
        if (text == null || text.isBlank()) {
            throw new IllegalArgumentException("text must not be blank");
        }
        text = text.trim();
    }
}
