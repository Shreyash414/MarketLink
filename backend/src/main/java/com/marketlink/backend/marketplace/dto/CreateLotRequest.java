package com.marketlink.backend.marketplace.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CreateLotRequest {

    @NotBlank(message = "Crop name is required")
    private String cropName;

    private String variety;

    @NotNull(message = "Quantity in kg is required")
    @DecimalMin(value = "1.0", message = "Quantity must be at least 1.0 kg")
    private Double quantityKg;

    @NotNull(message = "Base price per kg is required")
    @DecimalMin(value = "0.5", message = "Base price must be positive")
    private Double basePricePerKg;

    private String location;
}
