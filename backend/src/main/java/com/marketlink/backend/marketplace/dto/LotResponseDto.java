package com.marketlink.backend.marketplace.dto;

import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LotResponseDto {
    private UUID id;
    private UUID farmerId;
    private String cropName;
    private String variety;
    private Double quantityKg;
    private Double basePricePerKg;
    private LotStatus status;
    private String location;
    private Instant createdAt;

    public static LotResponseDto fromEntity(Lot lot) {
        return LotResponseDto.builder()
                .id(lot.getId())
                .farmerId(lot.getFarmerId())
                .cropName(lot.getCropName())
                .variety(lot.getVariety())
                .quantityKg(lot.getQuantityKg())
                .basePricePerKg(lot.getBasePricePerKg())
                .status(lot.getStatus())
                .location(lot.getLocation())
                .createdAt(lot.getCreatedAt())
                .build();
    }
}
