package com.marketlink.backend.marketprice.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PastOrPresent;
import jakarta.validation.constraints.Positive;
import lombok.*;

import java.time.LocalDate;
import java.util.UUID;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Request payload for recording a market price observation")
public class RecordMarketPriceRequest {

    @NotNull(message = "Crop ID is required")
    @Schema(description = "UUID of the crop", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", requiredMode = Schema.RequiredMode.REQUIRED)
    private UUID cropId;

    @NotNull(message = "Market ID is required")
    @Schema(description = "UUID of the APMC / Mandi market", example = "b2c3d4e5-f6a7-8901-bcde-f12345678901", requiredMode = Schema.RequiredMode.REQUIRED)
    private UUID marketId;

    @PastOrPresent(message = "Price date cannot be in the future")
    @Schema(description = "Date of price observation (defaults to today)", example = "2026-08-30")
    private LocalDate priceDate;

    @NotNull(message = "Minimum price is required")
    @Positive(message = "Minimum price must be positive")
    @Schema(description = "Minimum recorded trade price", example = "1800.0", requiredMode = Schema.RequiredMode.REQUIRED)
    private Double minPrice;

    @NotNull(message = "Maximum price is required")
    @Positive(message = "Maximum price must be positive")
    @Schema(description = "Maximum recorded trade price", example = "2600.0", requiredMode = Schema.RequiredMode.REQUIRED)
    private Double maxPrice;

    @NotNull(message = "Modal price is required")
    @Positive(message = "Modal price must be positive")
    @Schema(description = "Modal / most common trade price", example = "2200.0", requiredMode = Schema.RequiredMode.REQUIRED)
    private Double modalPrice;

    @Positive(message = "Arrival quantity must be positive")
    @Schema(description = "Reported market arrival quantity", example = "450.0")
    private Double arrivalQuantity;

    @Schema(description = "Price quotation unit (default QUINTAL)", example = "QUINTAL")
    @Builder.Default
    private String unit = "QUINTAL";

    @Schema(description = "Data source or reporting agency", example = "APMC_AGMARKNET")
    private String source;
}
