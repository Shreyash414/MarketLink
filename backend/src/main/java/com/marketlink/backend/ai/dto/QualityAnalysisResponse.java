package com.marketlink.backend.ai.dto;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.domain.quality.entity.QualityAnalysisResult;
import com.marketlink.backend.domain.quality.enums.QualityAnalysisStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.time.Instant;
import java.util.Collections;
import java.util.Map;
import java.util.UUID;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Response payload representing produce quality assessment results")
public class QualityAnalysisResponse {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    @Schema(description = "Unique identifier of the quality result record", example = "e5f6a7b8-1234-5678-9abc-def012345678")
    private UUID id;

    @Schema(description = "UUID of the evaluated produce lot", example = "c3d4e5f6-a7b8-9012-cdef-123456789012")
    private UUID lotId;

    @Schema(description = "Quality analysis lifecycle status", example = "COMPLETED")
    private QualityAnalysisStatus status;

    @Schema(description = "Calculated produce quality score", example = "88.5")
    private Double qualityScore;

    @Schema(description = "Assigned produce grade (e.g. A, B, PREMIUM)", example = "GRADE_A")
    private String grade;

    @Schema(description = "Model prediction confidence level", example = "0.94")
    private Double confidence;

    @Schema(description = "AI model provider identifier", example = "AGRI_VISION_MODEL")
    private String modelProvider;

    @Schema(description = "AI model version", example = "v2.1.0")
    private String modelVersion;

    @Schema(description = "Extracted physical and quality attributes (e.g. defect %, uniformity, color)")
    private Map<String, Object> attributes;

    @Schema(description = "Timestamp when analysis occurred")
    private Instant analyzedAt;

    @Schema(description = "Timestamp when record was registered")
    private Instant createdAt;

    public static QualityAnalysisResponse fromEntity(QualityAnalysisResult result) {
        if (result == null) {
            return null;
        }

        Map<String, Object> attrs = Collections.emptyMap();
        if (result.getAttributesJson() != null && !result.getAttributesJson().isBlank()) {
            try {
                attrs = OBJECT_MAPPER.readValue(result.getAttributesJson(), new TypeReference<Map<String, Object>>() {});
            } catch (Exception ignored) {
                // If parsing fails, attrs remains empty
            }
        }

        return QualityAnalysisResponse.builder()
                .id(result.getId())
                .lotId(result.getLotId())
                .status(result.getStatus())
                .qualityScore(result.getQualityScore())
                .grade(result.getGrade())
                .confidence(result.getConfidence())
                .modelProvider(result.getModelProvider())
                .modelVersion(result.getModelVersion())
                .attributes(attrs)
                .analyzedAt(result.getAnalyzedAt())
                .createdAt(result.getCreatedAt())
                .build();
    }
}
