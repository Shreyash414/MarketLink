package com.marketlink.backend.ai.dto.modelapp;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO matching Model-app MandiRecommendationRequest schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppRecommendationRequest {

    @NotNull(message = "Farmer latitude is required")
    @DecimalMin(value = "-90.0", message = "Latitude must be >= -90.0")
    @DecimalMax(value = "90.0", message = "Latitude must be <= 90.0")
    @JsonProperty("farmer_latitude")
    private Double farmerLatitude;

    @NotNull(message = "Farmer longitude is required")
    @DecimalMin(value = "-180.0", message = "Longitude must be >= -180.0")
    @DecimalMax(value = "180.0", message = "Longitude must be <= 180.0")
    @JsonProperty("farmer_longitude")
    private Double farmerLongitude;

    @NotNull(message = "Quantity in quintals is required")
    @Positive(message = "Quantity must be greater than 0")
    @JsonProperty("quantity_quintals")
    private Double quantityQuintals;

    @Builder.Default
    private String commodity = "Onion";

    @JsonProperty("max_distance_km")
    private Double maxDistanceKm;

    @Builder.Default
    @JsonProperty("top_n")
    private Integer topN = 5;
}
