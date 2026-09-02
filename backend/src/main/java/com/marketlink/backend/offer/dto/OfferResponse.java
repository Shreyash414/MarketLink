package com.marketlink.backend.offer.dto;

import com.marketlink.backend.domain.offer.entity.Offer;
import com.marketlink.backend.domain.offer.enums.OfferStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Response payload representing a buyer offer on a produce lot")
public class OfferResponse {

    @Schema(description = "Unique identifier of the offer", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private UUID id;

    @Schema(description = "UUID of the evaluated produce lot", example = "b2c3d4e5-f6a7-8901-bcde-f12345678901")
    private UUID lotId;

    @Schema(description = "Crop name of the lot", example = "ONION")
    private String cropName;

    @Schema(description = "UUID of the buyer who placed the offer", example = "c3d4e5f6-a7b8-9012-cdef-123456789012")
    private UUID buyerId;

    @Schema(description = "Business name of the buyer", example = "Mahalaxmi Agro Traders")
    private String buyerBusinessName;

    @Schema(description = "Price offered per unit", example = "32.5")
    private Double offeredPrice;

    @Schema(description = "Quantity requested", example = "500.0")
    private Double quantity;

    @Schema(description = "Unit of measurement", example = "KG")
    private String unit;

    @Schema(description = "Current lifecycle status of the offer", example = "PENDING")
    private OfferStatus status;

    @Schema(description = "Optional notes attached to offer")
    private String notes;

    @Schema(description = "Timestamp when offer was created")
    private Instant createdAt;

    @Schema(description = "Timestamp when offer was last updated")
    private Instant updatedAt;

    public static OfferResponse fromEntity(Offer offer) {
        if (offer == null) {
            return null;
        }
        return OfferResponse.builder()
                .id(offer.getId())
                .lotId(offer.getLotId())
                .buyerId(offer.getBuyerId())
                .offeredPrice(offer.getOfferedPrice())
                .quantity(offer.getQuantity())
                .status(offer.getStatus())
                .notes(offer.getNotes())
                .createdAt(offer.getCreatedAt())
                .updatedAt(offer.getUpdatedAt())
                .build();
    }
}
