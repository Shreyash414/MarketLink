package com.marketlink.backend.ai.dto.modelapp;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * DTO matching Model-app MandiRecommendationResponse schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppRecommendationResponse {

    private String commodity;

    @JsonProperty("farmer_latitude")
    private Double farmerLatitude;

    @JsonProperty("farmer_longitude")
    private Double farmerLongitude;

    @JsonProperty("quantity_quintals")
    private Double quantityQuintals;

    @JsonProperty("recommended_mandi")
    private String recommendedMandi;

    @JsonProperty("total_mandis_evaluated")
    private Integer totalMandisEvaluated;

    @JsonProperty("overall_data_source")
    private String overallDataSource;

    @Builder.Default
    private List<ModelAppMandiItem> recommendations = List.of();

    @JsonProperty("contract_metadata")
    private Map<String, Object> contractMetadata;
}
