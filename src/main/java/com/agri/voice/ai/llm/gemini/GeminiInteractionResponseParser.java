package com.agri.voice.ai.llm.gemini;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.springframework.stereotype.Component;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

@Component
final class GeminiInteractionResponseParser {

    private final ObjectMapper objectMapper;

    GeminiInteractionResponseParser(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    ParseResult parse(byte[] json) {
        if (json == null || json.length == 0) {
            return ParseResult.empty();
        }
        try {
            JsonNode root = objectMapper.readTree(json);
            if (root == null || !root.isObject() || !root.path("steps").isArray()) {
                return ParseResult.malformed();
            }
            List<String> textParts = new ArrayList<>();
            for (JsonNode step : root.path("steps")) {
                if (!"model_output".equals(step.path("type").asText())
                        || !step.path("content").isArray()) {
                    continue;
                }
                for (JsonNode part : step.path("content")) {
                    if ("text".equals(part.path("type").asText())
                            && part.path("text").isTextual()
                            && !part.path("text").asText().isBlank()) {
                        textParts.add(part.path("text").asText());
                    }
                }
            }
            if (textParts.isEmpty()) {
                return ParseResult.empty();
            }
            return ParseResult.success(String.join("", textParts).trim());
        } catch (IOException exception) {
            return ParseResult.malformed();
        }
    }

    record ParseResult(Status status, String text) {

        static ParseResult success(String text) {
            return new ParseResult(Status.SUCCESS, text);
        }

        static ParseResult malformed() {
            return new ParseResult(Status.MALFORMED, null);
        }

        static ParseResult empty() {
            return new ParseResult(Status.EMPTY, null);
        }

        enum Status {
            SUCCESS,
            MALFORMED,
            EMPTY
        }
    }
}
