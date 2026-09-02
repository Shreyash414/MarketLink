package com.marketlink.backend.marketplace.dto;

import com.marketlink.backend.domain.marketplace.entity.Bid;
import com.marketlink.backend.domain.marketplace.enums.BidStatus;
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
public class BidResponseDto {
    private UUID id;
    private UUID lotId;
    private UUID buyerId;
    private Double offeredPricePerKg;
    private Double totalQuantityKg;
    private BidStatus status;
    private Instant createdAt;

    public static BidResponseDto fromEntity(Bid bid) {
        return BidResponseDto.builder()
                .id(bid.getId())
                .lotId(bid.getLotId())
                .buyerId(bid.getBuyerId())
                .offeredPricePerKg(bid.getOfferedPricePerKg())
                .totalQuantityKg(bid.getTotalQuantityKg())
                .status(bid.getStatus())
                .createdAt(bid.getCreatedAt())
                .build();
    }
}
