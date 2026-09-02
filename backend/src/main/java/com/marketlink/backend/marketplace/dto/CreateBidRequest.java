package com.marketlink.backend.marketplace.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CreateBidRequest {

    @NotNull(message = "Lot ID is required")
    private UUID lotId;

    @NotNull(message = "Offered price per kg is required")
    @DecimalMin(value = "0.5", message = "Offered price must be positive")
    private Double offeredPricePerKg;

    @NotNull(message = "Total quantity is required")
    @DecimalMin(value = "1.0", message = "Quantity must be at least 1.0 kg")
    private Double totalQuantityKg;
}
