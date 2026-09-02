package com.marketlink.backend.market.dto;

import com.marketlink.backend.domain.market.entity.Market;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Response payload representing a market master record")
public class MarketResponse {

    @Schema(description = "Unique identifier of the market", example = "b2c3d4e5-f6a7-8901-bcde-f12345678901")
    private UUID id;

    @Schema(description = "Name of the market / APMC", example = "Pune APMC")
    private String name;

    @Schema(description = "District where market is situated", example = "Pune")
    private String district;

    @Schema(description = "State where market is situated", example = "Maharashtra")
    private String state;

    @Schema(description = "Geographic latitude", example = "18.5204")
    private Double latitude;

    @Schema(description = "Geographic longitude", example = "73.8567")
    private Double longitude;

    @Schema(description = "Whether the market is active for trade and price discovery", example = "true")
    private Boolean active;

    @Schema(description = "Timestamp when market was registered")
    private Instant createdAt;

    @Schema(description = "Timestamp when market was last updated")
    private Instant updatedAt;

    public static MarketResponse fromEntity(Market market) {
        if (market == null) {
            return null;
        }
        return MarketResponse.builder()
                .id(market.getId())
                .name(market.getName())
                .district(market.getDistrict())
                .state(market.getState())
                .latitude(market.getLatitude())
                .longitude(market.getLongitude())
                .active(market.getActive())
                .createdAt(market.getCreatedAt())
                .updatedAt(market.getUpdatedAt())
                .build();
    }
}
