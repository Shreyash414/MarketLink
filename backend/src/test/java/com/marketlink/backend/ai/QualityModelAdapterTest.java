package com.marketlink.backend.ai;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.ai.adapter.CustomGradingAiModelAdapter;
import com.marketlink.backend.ai.adapter.GenericJsonAiModelAdapter;
import com.marketlink.backend.ai.adapter.StandardAiModelAdapter;
import com.marketlink.backend.domain.quality.entity.QualityAnalysisResult;
import com.marketlink.backend.domain.quality.enums.QualityAnalysisStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class QualityModelAdapterTest {

    private ObjectMapper objectMapper;
    private StandardAiModelAdapter standardAdapter;
    private CustomGradingAiModelAdapter customAdapter;
    private GenericJsonAiModelAdapter genericAdapter;
    private UUID lotId;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        standardAdapter = new StandardAiModelAdapter(objectMapper);
        customAdapter = new CustomGradingAiModelAdapter(objectMapper);
        genericAdapter = new GenericJsonAiModelAdapter(objectMapper);
        lotId = UUID.randomUUID();
    }

    @Test
    @DisplayName("StandardAiModelAdapter correctly adapts standard model output")
    void testStandardAdapter() {
        Map<String, Object> standardPayload = Map.of(
                "quality", 0.88,
                "grade", "GRADE_A",
                "confidence", 0.95,
                "provider", "AGRI_VISION_V1",
                "version", "1.2.0",
                "attributes", Map.of("color", "RED", "defectPercentage", 1.2)
        );

        assertThat(standardAdapter.supports("AGRI_VISION")).isTrue();

        QualityAnalysisResult result = standardAdapter.adapt(lotId, standardPayload);

        assertThat(result).isNotNull();
        assertThat(result.getLotId()).isEqualTo(lotId);
        assertThat(result.getStatus()).isEqualTo(QualityAnalysisStatus.COMPLETED);
        assertThat(result.getQualityScore()).isEqualTo(0.88);
        assertThat(result.getGrade()).isEqualTo("GRADE_A");
        assertThat(result.getConfidence()).isEqualTo(0.95);
        assertThat(result.getModelProvider()).isEqualTo("AGRI_VISION_V1");
    }

    @Test
    @DisplayName("CustomGradingAiModelAdapter correctly adapts nested prediction payload")
    void testCustomGradingAdapter() {
        Map<String, Object> customPayload = Map.of(
                "prediction", Map.of(
                        "score", 92.0,
                        "category", "premium",
                        "certainty", 0.96
                ),
                "model_info", "DEEP_GRADER_V2",
                "version", "2.0"
        );

        assertThat(customAdapter.supports("DEEP_GRADER")).isTrue();

        QualityAnalysisResult result = customAdapter.adapt(lotId, customPayload);

        assertThat(result).isNotNull();
        assertThat(result.getLotId()).isEqualTo(lotId);
        assertThat(result.getStatus()).isEqualTo(QualityAnalysisStatus.COMPLETED);
        assertThat(result.getQualityScore()).isEqualTo(92.0);
        assertThat(result.getGrade()).isEqualTo("PREMIUM");
        assertThat(result.getConfidence()).isEqualTo(0.96);
        assertThat(result.getModelProvider()).isEqualTo("DEEP_GRADER_V2");
    }

    @Test
    @DisplayName("GenericJsonAiModelAdapter captures arbitrary JSON without error")
    void testGenericAdapter() {
        Map<String, Object> unknownPayload = Map.of(
                "custom_field_x", 12345,
                "unknown_metric", "HIGH"
        );

        QualityAnalysisResult result = genericAdapter.adapt(lotId, unknownPayload);

        assertThat(result).isNotNull();
        assertThat(result.getLotId()).isEqualTo(lotId);
        assertThat(result.getStatus()).isEqualTo(QualityAnalysisStatus.COMPLETED);
        assertThat(result.getAttributesJson()).contains("custom_field_x");
    }
}
