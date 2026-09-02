package com.marketlink.backend.lot.dto;

import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Response payload representing an agricultural produce lot")
public class LotResponse {

    @Schema(description = "Unique identifier of the lot", example = "c3d4e5f6-a7b8-9012-cdef-123456789012")
    private UUID id;

    @Schema(description = "UUID of the farmer who owns the lot", example = "d4e5f6a7-b8c9-0123-def1-234567890123")
    private UUID farmerId;

    @Schema(description = "UUID of the master crop record", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private UUID cropId;

    @Schema(description = "Name of the crop", example = "ONION")
    private String cropName;

    @Schema(description = "UUID of the associated market", example = "b2c3d4e5-f6a7-8901-bcde-f12345678901")
    private UUID marketId;

    @Schema(description = "Name of the associated market", example = "Pune APMC")
    private String marketName;

    @Schema(description = "Variety or cultivar", example = "Nashik Red")
    private String variety;

    @Schema(description = "Quantity of produce", example = "500.0")
    private Double quantity;

    @Schema(description = "Unit of measurement", example = "KG")
    private String unit;

    @Schema(description = "Harvest date", example = "2026-08-25")
    private LocalDate harvestDate;

    @Schema(description = "Expected price per unit", example = "35.0")
    private Double expectedPrice;

    @Schema(description = "Minimum acceptable price per unit", example = "30.0")
    private Double minimumAcceptablePrice;

    @Schema(description = "Current lifecycle status of the lot", example = "PUBLISHED")
    private LotStatus status;

    @Schema(description = "Location / farm origin", example = "Khed, Pune, Maharashtra")
    private String location;

    @Schema(description = "Timestamp when lot was created")
    private Instant createdAt;

    @Schema(description = "Timestamp when lot was last updated")
    private Instant updatedAt;

    public static LotResponse fromEntity(Lot lot) {
        if (lot == null) {
            return null;
        }
        return LotResponse.builder()
                .id(lot.getId())
                .farmerId(lot.getFarmerId())
                .cropId(lot.getCropId())
                .cropName(lot.getCropName())
                .marketId(lot.getMarketId())
                .variety(lot.getVariety())
                .quantity(lot.getQuantity())
                .unit(lot.getUnit())
                .harvestDate(lot.getHarvestDate())
                .expectedPrice(lot.getExpectedPrice())
                .minimumAcceptablePrice(lot.getMinimumAcceptablePrice())
                .status(lot.getStatus())
                .location(lot.getLocation())
                .createdAt(lot.getCreatedAt())
                .updatedAt(lot.getUpdatedAt())
                .build();
    }
}
