package com.marketlink.backend.ai.dto.modelapp;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO matching Model-app SinglePredictionResponse schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppPredictionResponse {

    private String market;
    private String commodity;

    @JsonProperty("current_price")
    private Double currentPrice;

    @JsonProperty("predicted_price")
    private Double predictedPrice;

    @JsonProperty("expected_change")
    private Double expectedChange;

    @JsonProperty("expected_change_pct")
    private Double expectedChangePct;

    @JsonProperty("expected_direction")
    private String expectedDirection;

    @JsonProperty("usage_status")
    private String usageStatus;

    @JsonProperty("reliability_score")
    private Double reliabilityScore;

    @JsonProperty("quality_class")
    private String qualityClass;

    @JsonProperty("data_source")
    private String dataSource;

    private String warning;
}
