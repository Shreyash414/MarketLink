package com.marketlink.backend.market.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Size;
import lombok.*;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Request payload for updating an existing market record")
public class UpdateMarketRequest {

    @Size(min = 2, max = 150, message = "Market name must be between 2 and 150 characters")
    @Schema(description = "Updated market / APMC name", example = "Pune Central APMC")
    private String name;

    @Size(min = 2, max = 100, message = "District must be between 2 and 100 characters")
    @Schema(description = "Updated district", example = "Pune")
    private String district;

    @Size(min = 2, max = 100, message = "State must be between 2 and 100 characters")
    @Schema(description = "Updated state", example = "Maharashtra")
    private String state;

    @DecimalMin(value = "-90.0", message = "Latitude must be >= -90.0")
    @DecimalMax(value = "90.0", message = "Latitude must be <= 90.0")
    @Schema(description = "Updated latitude", example = "18.5204")
    private Double latitude;

    @DecimalMin(value = "-180.0", message = "Longitude must be >= -180.0")
    @DecimalMax(value = "180.0", message = "Longitude must be <= 180.0")
    @Schema(description = "Updated longitude", example = "73.8567")
    private Double longitude;

    @Schema(description = "Active status of the market", example = "true")
    private Boolean active;
}
