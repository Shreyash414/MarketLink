package com.agri.voice.ai.stt.gemini;

import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

final class GeminiProtocol {

    private final ObjectMapper objectMapper;

    GeminiProtocol(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    String setup(GeminiSttProperties properties) {
        Map<String, Object> transcription = new LinkedHashMap<>();
        transcription.put("languageCodes", clean(properties.getLanguageCodes()));
        List<String> vocabulary = clean(properties.getCustomVocabulary());
        if (!vocabulary.isEmpty()) {
            transcription.put("customVocabulary", vocabulary);
        }
        transcription.put("mode", properties.getMode().trim().toUpperCase());

        Map<String, Object> setup = new LinkedHashMap<>();
        setup.put("model", "models/" + properties.getModel().trim());
        setup.put("generationConfig", Map.of("responseModalities", List.of("TEXT")));
        setup.put("inputAudioTranscription", transcription);
        return write(Map.of("setup", setup));
    }

    String audio(byte[] pcm16) {
        Map<String, Object> blob = Map.of(
                "data", Base64.getEncoder().encodeToString(pcm16),
                "mimeType", "audio/pcm;rate=16000");
        return write(Map.of("realtimeInput", Map.of("audio", blob)));
    }

    String audioStreamEnd() {
        return write(Map.of("realtimeInput", Map.of("audioStreamEnd", true)));
    }

    private List<String> clean(List<String> values) {
        if (values == null) {
            return List.of();
        }
        return values.stream()
                .filter(value -> value != null && !value.isBlank())
                .map(String::trim)
                .distinct()
                .toList();
    }

    private String write(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Gemini protocol message could not be serialized");
        }
    }
}
