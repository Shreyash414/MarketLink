package com.marketlink.backend.ai.adapter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.domain.quality.entity.QualityAnalysisResult;
import com.marketlink.backend.domain.quality.enums.QualityAnalysisStatus;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.UUID;

/**
 * Fallback generic adapter for any JSON / Map structure.
 */
@Slf4j
@Component
@Order(100)
@RequiredArgsConstructor
public class GenericJsonAiModelAdapter implements QualityModelAdapter {

    private final ObjectMapper objectMapper;

    @Override
    public boolean supports(String modelProvider) {
        return true; // Default fallback
    }

    @Override
    public QualityAnalysisResult adapt(UUID lotId, Object rawModelOutput) {
        try {
            String json = objectMapper.writeValueAsString(rawModelOutput);
            return QualityAnalysisResult.builder()
                    .lotId(lotId)
                    .status(QualityAnalysisStatus.COMPLETED)
                    .modelProvider("GENERIC_AI_MODEL")
                    .modelVersion("1.0")
                    .attributesJson(json)
                    .rawMetadata(json)
                    .analyzedAt(Instant.now())
                    .build();
        } catch (Exception e) {
            log.error("GenericJsonAiModelAdapter failed: {}", e.getMessage());
            return QualityAnalysisResult.builder()
                    .lotId(lotId)
                    .status(QualityAnalysisStatus.FAILED)
                    .modelProvider("GENERIC_AI_MODEL")
                    .rawMetadata("{\"error\":\"" + e.getMessage() + "\"}")
                    .analyzedAt(Instant.now())
                    .build();
        }
    }
}
