package com.marketlink.backend.ai.dto.modelapp;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO matching Model-app MandiItemResponse schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppMandiItem {

    private Integer rank;
    private String mandi;
    private String state;
    private String district;

    @JsonProperty("distance_km")
    private Double distanceKm;

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

    @JsonProperty("transport_cost")
    private Double transportCost;

    @JsonProperty("market_fee")
    private Double marketFee;

    @JsonProperty("gross_revenue")
    private Double grossRevenue;

    @JsonProperty("total_cost")
    private Double totalCost;

    @JsonProperty("net_return")
    private Double netReturn;

    @JsonProperty("net_price_per_quintal")
    private Double netPricePerQuintal;

    @JsonProperty("risk_level")
    private String riskLevel;

    @JsonProperty("confidence_score")
    private Double confidenceScore;

    @JsonProperty("recommendation_label")
    private String recommendationLabel;

    @JsonProperty("model_usage_status")
    private String modelUsageStatus;

    @JsonProperty("model_reliability_score")
    private Double modelReliabilityScore;

    @JsonProperty("model_quality_class")
    private String modelQualityClass;

    @JsonProperty("data_source")
    private String dataSource;

    @JsonProperty("data_freshness_status")
    private String dataFreshnessStatus;

    @JsonProperty("data_age_days")
    private Integer dataAgeDays;

    @JsonProperty("historical_session_count")
    private Integer historicalSessionCount;

    @JsonProperty("data_reliability_status")
    private String dataReliabilityStatus;

    @JsonProperty("data_reliability_warning")
    private String dataReliabilityWarning;

    private String warning;
}
