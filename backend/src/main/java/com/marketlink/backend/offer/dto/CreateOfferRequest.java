package com.marketlink.backend.offer.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import lombok.*;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Request payload for buyer creating an offer on a published lot")
public class CreateOfferRequest {

    @NotNull(message = "Offered price is required")
    @Positive(message = "Offered price must be strictly greater than 0")
    @Schema(description = "Price offered per unit", example = "32.5", requiredMode = Schema.RequiredMode.REQUIRED)
    private Double offeredPrice;

    @NotNull(message = "Quantity is required")
    @Positive(message = "Quantity must be strictly greater than 0")
    @Schema(description = "Quantity of produce requested in this offer", example = "500.0", requiredMode = Schema.RequiredMode.REQUIRED)
    private Double quantity;

    @Size(max = 500, message = "Notes cannot exceed 500 characters")
    @Schema(description = "Optional note or delivery terms to farmer", example = "Self-pickup within 48 hours")
    private String notes;
}
