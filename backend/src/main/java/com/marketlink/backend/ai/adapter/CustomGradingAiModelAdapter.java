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
 * Adapter for models returning custom/nested structure:
 * {
 *   "prediction": {
 *     "score": 87,
 *     "category": "premium",
 *     "certainty": 0.92
 *   },
 *   "model_info": "CUSTOM_DEEP_GRADER",
 *   "version": "2.0"
 * }
 */
@Slf4j
@Component
@Order(2)
@RequiredArgsConstructor
public class CustomGradingAiModelAdapter implements QualityModelAdapter {

    private final ObjectMapper objectMapper;

    @Override
    public boolean supports(String modelProvider) {
        return modelProvider != null && (modelProvider.equalsIgnoreCase("CUSTOM")
                || modelProvider.toUpperCase().contains("PREDICTION")
                || modelProvider.toUpperCase().contains("DEEP_GRADER"));
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
            String grade = "STANDARD";
            Double confidence = 1.0;

            if (map.containsKey("prediction") && map.get("prediction") instanceof Map) {
                Map<String, Object> pred = (Map<String, Object>) map.get("prediction");
                if (pred.containsKey("score")) {
                    score = ((Number) pred.get("score")).doubleValue();
                }
                if (pred.containsKey("category")) {
                    grade = ((String) pred.get("category")).toUpperCase();
                }
                if (pred.containsKey("certainty")) {
                    confidence = ((Number) pred.get("certainty")).doubleValue();
                }
            }

            String provider = (String) map.getOrDefault("model_info", "CUSTOM_MODEL");
            String version = (String) map.getOrDefault("version", "v2.0");
            String rawJson = objectMapper.writeValueAsString(rawModelOutput);

            return QualityAnalysisResult.builder()
                    .lotId(lotId)
                    .status(QualityAnalysisStatus.COMPLETED)
                    .qualityScore(score)
                    .grade(grade)
                    .confidence(confidence)
                    .modelProvider(provider)
                    .modelVersion(version)
                    .attributesJson(rawJson)
                    .rawMetadata(rawJson)
                    .analyzedAt(Instant.now())
                    .build();

        } catch (Exception e) {
            log.error("CustomGradingAiModelAdapter failed to adapt payload: {}", e.getMessage());
            return QualityAnalysisResult.builder()
                    .lotId(lotId)
                    .status(QualityAnalysisStatus.FAILED)
                    .modelProvider("CUSTOM_MODEL")
                    .rawMetadata("{\"error\":\"" + e.getMessage() + "\"}")
                    .analyzedAt(Instant.now())
                    .build();
        }
    }
}
