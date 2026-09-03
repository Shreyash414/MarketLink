package com.agri.voice.ai.stt.gemini;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.regex.Pattern;

import org.springframework.stereotype.Component;

import com.agri.voice.ai.stt.TranscriptType;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

@Component
public final class GeminiResponseParser {

    private static final int MAX_DIAGNOSTIC_FIELDS = 16;
    private static final Pattern SAFE_FIELD_NAME = Pattern.compile("[A-Za-z][A-Za-z0-9_]{0,63}");

    private final ObjectMapper objectMapper;

    public GeminiResponseParser(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public ParseResult parse(String json) {
        if (json == null || json.isBlank()) {
            return ParseResult.malformed();
        }
        try {
            JsonNode root = objectMapper.readTree(json);
            if (root == null || !root.isObject()) {
                return ParseResult.malformed();
            }

            boolean setupComplete = root.has("setupComplete");
            List<String> topLevelFields = fieldNames(root);
            List<ParsedTranscript> transcripts = new ArrayList<>(2);
            JsonNode content = root.get("serverContent");
            List<String> serverContentFields = List.of();
            if (content != null && content.isObject()) {
                serverContentFields = fieldNames(content);
                addTranscript(content.get("interimInputTranscription"), TranscriptType.INTERIM, transcripts);
                addTranscript(content.get("inputTranscription"), TranscriptType.FINAL, transcripts);
            }
            return ParseResult.success(
                    setupComplete,
                    List.copyOf(transcripts),
                    topLevelFields,
                    serverContentFields,
                    providerError(root.get("error")));
        } catch (JsonProcessingException exception) {
            return ParseResult.malformed();
        }
    }

    private void addTranscript(
            JsonNode transcription,
            TranscriptType type,
            List<ParsedTranscript> destination) {
        if (transcription == null || !transcription.isObject()) {
            return;
        }
        JsonNode textNode = transcription.get("text");
        if (textNode != null && textNode.isTextual() && !textNode.asText().isBlank()) {
            destination.add(new ParsedTranscript(textNode.asText(), type));
        }
    }

    private List<String> fieldNames(JsonNode object) {
        List<String> fields = new ArrayList<>();
        Iterator<String> names = object.fieldNames();
        while (names.hasNext() && fields.size() < MAX_DIAGNOSTIC_FIELDS) {
            String name = names.next();
            fields.add(SAFE_FIELD_NAME.matcher(name).matches() ? name : "[other]");
        }
        return List.copyOf(fields);
    }

    private ProviderError providerError(JsonNode error) {
        if (error == null || !error.isObject()) {
            return null;
        }
        Integer code = error.path("code").canConvertToInt() ? error.path("code").intValue() : null;
        String status = error.path("status").isTextual() ? error.path("status").textValue() : null;
        String message = error.path("message").isTextual() ? error.path("message").textValue() : null;
        return new ProviderError(code, status, message);
    }

    public record ParsedTranscript(String text, TranscriptType type) {
    }

    public record ProviderError(Integer code, String status, String message) {
    }

    public record ParseResult(
            boolean successful,
            boolean setupComplete,
            List<ParsedTranscript> transcripts,
            List<String> topLevelFields,
            List<String> serverContentFields,
            ProviderError providerError) {

        static ParseResult success(
                boolean setupComplete,
                List<ParsedTranscript> transcripts,
                List<String> topLevelFields,
                List<String> serverContentFields,
                ProviderError providerError) {
            return new ParseResult(
                    true,
                    setupComplete,
                    transcripts,
                    topLevelFields,
                    serverContentFields,
                    providerError);
        }

        static ParseResult malformed() {
            return new ParseResult(false, false, List.of(), List.of(), List.of(), null);
        }
    }
}
