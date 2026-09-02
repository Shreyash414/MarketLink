package com.marketlink.backend.ai.adapter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.domain.quality.entity.QualityAnalysisResult;
import com.marketlink.backend.domain.quality.enums.QualityAnalysisStatus;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * Adapter for models returning standard structure:
 * {
 *   "quality": 0.88,
 *   "grade": "A",
 *   "confidence": 0.94,
 *   "provider": "AGRI_VISION",
 *   "version": "1.0",
 *   "attributes": { ... }
 * }
 */
@Slf4j
@Component
@Order(1)
@RequiredArgsConstructor
public class StandardAiModelAdapter implements QualityModelAdapter {

    private final ObjectMapper objectMapper;

    @Override
    public boolean supports(String modelProvider) {
        return modelProvider == null || modelProvider.equalsIgnoreCase("STANDARD") || modelProvider.toUpperCase().contains("AGRI_VISION");
    }

    @Override
    @SuppressWarnings("unchecked")
    public QualityAnalysisResult adapt(UUID lotId, Object rawModelOutput) {
        try {
            Map<String, Object> map;
            if (rawModelOutput instanceof Map) {
                map = (Map<String, Object>) rawModelOutput;
            } else {
                map = objectMapper.convertValue(rawModelOutput, Map.class);
            }

            Double score = null;
            if (map.containsKey("quality")) {
                score = ((Number) map.get("quality")).doubleValue();
            } else if (map.containsKey("qualityScore")) {
                score = ((Number) map.get("qualityScore")).doubleValue();
            }

            String grade = (String) map.getOrDefault("grade", "STANDARD");
            Double confidence = map.containsKey("confidence") ? ((Number) map.get("confidence")).doubleValue() : 1.0;
            String provider = (String) map.getOrDefault("provider", "STANDARD_MODEL");
            String version = (String) map.getOrDefault("version", "v1.0");

            Object attributesObj = map.get("attributes");
            String attributesJson = attributesObj != null ? objectMapper.writeValueAsString(attributesObj) : "{}";
            String rawJson = objectMapper.writeValueAsString(rawModelOutput);

            return QualityAnalysisResult.builder()
                    .lotId(lotId)
                    .status(QualityAnalysisStatus.COMPLETED)
                    .qualityScore(score)
                    .grade(grade)
                    .confidence(confidence)
                    .modelProvider(provider)
                    .modelVersion(version)
                    .attributesJson(attributesJson)
                    .rawMetadata(rawJson)
                    .analyzedAt(Instant.now())
                    .build();

        } catch (Exception e) {
            log.error("StandardAiModelAdapter failed to adapt payload: {}", e.getMessage());
            return fallbackFailedResult(lotId, rawModelOutput, e.getMessage());
        }
    }

    private QualityAnalysisResult fallbackFailedResult(UUID lotId, Object rawModelOutput, String error) {
        return QualityAnalysisResult.builder()
                .lotId(lotId)
                .status(QualityAnalysisStatus.FAILED)
                .modelProvider("STANDARD_MODEL")
                .rawMetadata("{\"error\":\"" + error + "\"}")
                .analyzedAt(Instant.now())
                .build();
    }
}
