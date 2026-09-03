package com.marketlink.backend.ai.dto.query;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.marketlink.backend.domain.common.entity.Location;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Universal request payload for farmer natural-language queries.
 * Carries natural language text plus optional domain context (crop, location, quantity, market).
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AiNaturalLanguageQueryRequest {

    @NotBlank(message = "Query text is required")
    private String query;

    @Builder.Default
    private String language = "en";

    private String crop;

    private String market;

    @Valid
    private Location location;

    @JsonProperty("quantity_quintals")
    private Double quantityQuintals;

    @JsonProperty("max_distance_km")
    private Double maxDistanceKm;

    @JsonProperty("current_price")
    private Double currentPrice;

    /**
     * Resolves effective commodity, defaulting to "Onion" if not specified.
     */
    public String resolveCommodity() {
        if (crop != null && !crop.isBlank()) {
            return crop.trim();
        }
        return "Onion";
    }

    /**
     * Resolves effective quantity in quintals, defaulting to 10.0 if not specified.
     */
    public double resolveQuantityQuintals() {
        if (quantityQuintals != null && quantityQuintals > 0) {
            return quantityQuintals;
        }
        return 10.0;
    }
}
