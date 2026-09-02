package com.marketlink.backend.marketprice.dto;

import com.marketlink.backend.domain.marketprice.entity.MarketPrice;
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
@Schema(description = "Response payload representing a market price observation")
public class MarketPriceResponse {

    @Schema(description = "Unique identifier of the price record", example = "f6a7b8c9-1234-5678-9abc-def012345678")
    private UUID id;

    @Schema(description = "UUID of the crop", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private UUID cropId;

    @Schema(description = "Name of the crop", example = "ONION")
    private String cropName;

    @Schema(description = "UUID of the APMC / Mandi market", example = "b2c3d4e5-f6a7-8901-bcde-f12345678901")
    private UUID marketId;

    @Schema(description = "Name of the APMC / Mandi market", example = "Pune APMC")
    private String marketName;

    @Schema(description = "District where market is situated", example = "Pune")
    private String district;

    @Schema(description = "State where market is situated", example = "Maharashtra")
    private String state;

    @Schema(description = "Date of price observation", example = "2026-08-30")
    private LocalDate priceDate;

    @Schema(description = "Minimum recorded trade price", example = "1800.0")
    private Double minPrice;

    @Schema(description = "Maximum recorded trade price", example = "2600.0")
    private Double maxPrice;

    @Schema(description = "Modal / most common trade price", example = "2200.0")
    private Double modalPrice;

    @Schema(description = "Reported market arrival quantity", example = "450.0")
    private Double arrivalQuantity;

    @Schema(description = "Price quotation unit", example = "QUINTAL")
    private String unit;

    @Schema(description = "Reporting data source", example = "APMC_AGMARKNET")
    private String source;

    @Schema(description = "Timestamp when price record was created")
    private Instant createdAt;

    public static MarketPriceResponse fromEntity(MarketPrice mp) {
        if (mp == null) {
            return null;
        }
        return MarketPriceResponse.builder()
                .id(mp.getId())
                .cropId(mp.getCropId())
                .marketId(mp.getMarketId())
                .priceDate(mp.getPriceDate())
                .minPrice(mp.getMinPrice())
                .maxPrice(mp.getMaxPrice())
                .modalPrice(mp.getModalPrice())
                .arrivalQuantity(mp.getArrivalQuantity())
                .unit(mp.getUnit())
                .source(mp.getSource())
                .createdAt(mp.getCreatedAt())
                .build();
    }
}
