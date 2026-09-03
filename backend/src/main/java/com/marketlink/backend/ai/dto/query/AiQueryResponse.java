package com.marketlink.backend.ai.dto.query;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.marketlink.backend.ai.dto.modelapp.*;
import com.marketlink.backend.ai.enums.AiQueryIntent;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Universal response envelope for AI queries.
 * Contains classified intent, human-readable summary, and capability-specific structured payload.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AiQueryResponse {

    @JsonProperty("type")
    private AiQueryIntent intent;

    private Double confidence;

    private String answer;

    private ModelAppPredictionResponse prediction;

    private ModelAppRecommendationResponse recommendation;

    @JsonProperty("market_data")
    private ModelAppMarketDataResponse marketData;

    @JsonProperty("general_advisory")
    private ModelAppQueryResponse generalAdvisory;

    private String explanation;

    @Builder.Default
    private Instant timestamp = Instant.now();
}
