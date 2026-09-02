package com.marketlink.backend.ai.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.util.Map;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Request payload for recording AI model quality analysis result")
public class RecordQualityResultRequest {

    @Schema(description = "Overall quality score (e.g. 0.0 to 100.0 or 0.0 to 1.0)", example = "88.5")
    private Double qualityScore;

    @Schema(description = "Standardized grade assigned to produce", example = "GRADE_A")
    private String grade;

    @Schema(description = "Model prediction confidence level (0.0 to 1.0)", example = "0.94")
    private Double confidence;

    @Schema(description = "Name/identifier of the AI model provider", example = "AGRI_VISION_MODEL")
    private String modelProvider;

    @Schema(description = "Version of the AI model used", example = "v2.1.0")
    private String modelVersion;

    @Schema(description = "Dynamic produce attributes (e.g. color, size, defects, ripeness)")
    private Map<String, Object> attributes;

    @Schema(description = "Raw external JSON/object response from AI model")
    private Object rawPayload;
}
