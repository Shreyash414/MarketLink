package com.marketlink.backend.crop.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.*;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Request payload for creating a new crop master record")
public class CreateCropRequest {

    @NotBlank(message = "Crop name is required")
    @Size(min = 2, max = 100, message = "Crop name must be between 2 and 100 characters")
    @Schema(description = "Official/common name of the crop", example = "ONION", requiredMode = Schema.RequiredMode.REQUIRED)
    private String name;

    @NotBlank(message = "Category is required")
    @Size(min = 2, max = 100, message = "Category must be between 2 and 100 characters")
    @Schema(description = "Agricultural category of the crop", example = "VEGETABLE", requiredMode = Schema.RequiredMode.REQUIRED)
    private String category;

    @NotBlank(message = "Standard unit is required")
    @Size(min = 1, max = 20, message = "Unit must be between 1 and 20 characters")
    @Schema(description = "Standard unit of measurement", example = "KG", requiredMode = Schema.RequiredMode.REQUIRED)
    private String unit;
}
