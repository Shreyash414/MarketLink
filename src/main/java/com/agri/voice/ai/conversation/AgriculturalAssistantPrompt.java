package com.agri.voice.ai.conversation;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

@Component
final class AgriculturalAssistantPrompt {

    private static final String PROMPT_RESOURCE = "prompts/agricultural-assistant.txt";

    private final String text;

    AgriculturalAssistantPrompt(ConversationProperties properties) {
        String override = properties.getSystemInstructionOverride();
        this.text = override == null || override.isBlank() ? loadPrompt() : override.trim();
    }

    String text() {
        return text;
    }

    private String loadPrompt() {
        try (InputStream input = new ClassPathResource(PROMPT_RESOURCE).getInputStream()) {
            String prompt = new String(input.readAllBytes(), StandardCharsets.UTF_8).trim();
            if (prompt.isEmpty()) {
                throw new IllegalStateException("Agricultural assistant prompt is empty");
            }
            return prompt;
        } catch (IOException exception) {
            throw new IllegalStateException("Agricultural assistant prompt could not be loaded", exception);
        }
    }
}
