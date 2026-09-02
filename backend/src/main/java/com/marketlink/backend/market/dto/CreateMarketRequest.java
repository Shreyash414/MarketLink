package com.marketlink.backend.market.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.*;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Request payload for creating a new APMC / Mandi market record")
public class CreateMarketRequest {

    @NotBlank(message = "Market name is required")
    @Size(min = 2, max = 150, message = "Market name must be between 2 and 150 characters")
    @Schema(description = "Official market / APMC name", example = "Pune APMC", requiredMode = Schema.RequiredMode.REQUIRED)
    private String name;

    @NotBlank(message = "District is required")
    @Size(min = 2, max = 100, message = "District must be between 2 and 100 characters")
    @Schema(description = "District where market is situated", example = "Pune", requiredMode = Schema.RequiredMode.REQUIRED)
    private String district;

    @NotBlank(message = "State is required")
    @Size(min = 2, max = 100, message = "State must be between 2 and 100 characters")
    @Schema(description = "State where market is situated", example = "Maharashtra", requiredMode = Schema.RequiredMode.REQUIRED)
    private String state;

    @DecimalMin(value = "-90.0", message = "Latitude must be >= -90.0")
    @DecimalMax(value = "90.0", message = "Latitude must be <= 90.0")
    @Schema(description = "Geographic latitude of market", example = "18.5204")
    private Double latitude;

    @DecimalMin(value = "-180.0", message = "Longitude must be >= -180.0")
    @DecimalMax(value = "180.0", message = "Longitude must be <= 180.0")
    @Schema(description = "Geographic longitude of market", example = "73.8567")
    private Double longitude;
}
