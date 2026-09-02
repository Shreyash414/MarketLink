package com.marketlink.backend.crop.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Size;
import lombok.*;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Request payload for updating an existing crop master record")
public class UpdateCropRequest {

    @Size(min = 2, max = 100, message = "Crop name must be between 2 and 100 characters")
    @Schema(description = "Updated name of the crop", example = "RED ONION")
    private String name;

    @Size(min = 2, max = 100, message = "Category must be between 2 and 100 characters")
    @Schema(description = "Updated category of the crop", example = "VEGETABLE")
    private String category;

    @Size(min = 1, max = 20, message = "Unit must be between 1 and 20 characters")
    @Schema(description = "Updated standard unit of measurement", example = "KG")
    private String unit;

    @Schema(description = "Whether the crop is active for trade and listing", example = "true")
    private Boolean active;
}
