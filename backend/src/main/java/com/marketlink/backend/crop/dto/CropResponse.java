package com.marketlink.backend.crop.dto;

import com.marketlink.backend.domain.crop.entity.Crop;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Response payload representing a crop master record")
public class CropResponse {

    @Schema(description = "Unique identifier of the crop", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private UUID id;

    @Schema(description = "Name of the crop", example = "ONION")
    private String name;

    @Schema(description = "Category of the crop", example = "VEGETABLE")
    private String category;

    @Schema(description = "Standard unit of measurement", example = "KG")
    private String unit;

    @Schema(description = "Active status for marketplace listing and price tracking", example = "true")
    private Boolean active;

    @Schema(description = "Timestamp when crop was registered")
    private Instant createdAt;

    @Schema(description = "Timestamp when crop was last updated")
    private Instant updatedAt;

    public static CropResponse fromEntity(Crop crop) {
        if (crop == null) {
            return null;
        }
        return CropResponse.builder()
                .id(crop.getId())
                .name(crop.getName())
                .category(crop.getCategory())
                .unit(crop.getUnit())
                .active(crop.getActive())
                .createdAt(crop.getCreatedAt())
                .updatedAt(crop.getUpdatedAt())
                .build();
    }
}
