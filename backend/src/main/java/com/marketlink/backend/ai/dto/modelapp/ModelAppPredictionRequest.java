package com.marketlink.backend.ai.dto.modelapp;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * DTO matching Model-app SinglePredictionRequest schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppPredictionRequest {

    @NotBlank(message = "Market is required")
    private String market;

    @Builder.Default
    private String commodity = "Onion";

    @NotNull(message = "Current price is required")
    @Positive(message = "Current price must be positive")
    @JsonProperty("current_price")
    private Double currentPrice;

    @Builder.Default
    private Map<String, Double> features = Map.of();

    @Builder.Default
    @JsonProperty("farmer_facing")
    private Boolean farmerFacing = false;
}
