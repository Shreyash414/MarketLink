package com.marketlink.backend.lot.dto;

import io.swagger.v3.oas.annotations.media.Schema;
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
@Schema(description = "Request payload for farmer creating a new agricultural produce lot")
public class CreateLotRequest {

    @Schema(description = "UUID of the master crop (optional if cropName is supplied)", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private UUID cropId;

    @Schema(description = "Common or trade name of the crop", example = "ONION")
    private String cropName;

    @Schema(description = "UUID of the preferred APMC / Mandi market", example = "b2c3d4e5-f6a7-8901-bcde-f12345678901")
    private UUID marketId;

    @Schema(description = "Variety or cultivar of the crop", example = "Nashik Red")
    private String variety;

    @Positive(message = "Quantity must be strictly greater than 0")
    @Schema(description = "Quantity of produce in the lot", example = "500.0", requiredMode = Schema.RequiredMode.REQUIRED)
    private Double quantity;

    @Schema(description = "Standard unit of measurement (defaults to KG)", example = "KG")
    @Builder.Default
    private String unit = "KG";

    @PastOrPresent(message = "Harvest date cannot be in the future")
    @Schema(description = "Date when produce was harvested", example = "2026-08-25")
    private LocalDate harvestDate;

    @Positive(message = "Expected price must be strictly greater than 0")
    @Schema(description = "Farmer's target/expected price per unit", example = "35.0", requiredMode = Schema.RequiredMode.REQUIRED)
    private Double expectedPrice;

    @Positive(message = "Minimum acceptable price must be strictly greater than 0")
    @Schema(description = "Minimum floor price per unit acceptable to farmer", example = "30.0")
    private Double minimumAcceptablePrice;

    @Schema(description = "Geographic origin or farm location", example = "Khed, Pune, Maharashtra")
    private String location;
}
