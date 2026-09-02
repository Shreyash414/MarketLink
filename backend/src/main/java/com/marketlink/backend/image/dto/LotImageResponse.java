package com.marketlink.backend.image.dto;

import com.marketlink.backend.domain.image.entity.LotImage;
import com.marketlink.backend.domain.image.enums.ImageProcessingStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Response payload containing metadata for an uploaded produce photo")
public class LotImageResponse {

    @Schema(description = "Unique identifier of the image record", example = "d4e5f6a7-1234-5678-9abc-def012345678")
    private UUID id;

    @Schema(description = "UUID of the associated produce lot", example = "c3d4e5f6-a7b8-9012-cdef-123456789012")
    private UUID lotId;

    @Schema(description = "Original filename submitted during upload", example = "onion_harvest.jpg")
    private String originalFilename;

    @Schema(description = "MIME content type of the compressed image", example = "image/jpeg")
    private String contentType;

    @Schema(description = "Compressed image size in bytes", example = "154820")
    private Long fileSize;

    @Schema(description = "Image width in pixels", example = "1200")
    private Integer width;

    @Schema(description = "Image height in pixels", example = "900")
    private Integer height;

    @Schema(description = "Type/purpose of the photo", example = "PRODUCE_PHOTO")
    private String imageType;

    @Schema(description = "Processing status of the image", example = "PROCESSED")
    private ImageProcessingStatus processingStatus;

    @Schema(description = "Direct stream URL for retrieving raw binary JPEG photo", example = "/api/v1/lots/c3d4e5f6-a7b8-9012-cdef-123456789012/images/d4e5f6a7-1234-5678-9abc-def012345678")
    private String downloadUrl;

    @Schema(description = "Timestamp when image was uploaded")
    private Instant createdAt;

    public static LotImageResponse fromEntity(LotImage image) {
        if (image == null) {
            return null;
        }
        return LotImageResponse.builder()
                .id(image.getId())
                .lotId(image.getLotId())
                .originalFilename(image.getOriginalFilename())
                .contentType(image.getContentType())
                .fileSize(image.getFileSize())
                .width(image.getWidth())
                .height(image.getHeight())
                .imageType(image.getImageType())
                .processingStatus(image.getProcessingStatus())
                .downloadUrl("/api/v1/lots/" + image.getLotId() + "/images/" + image.getId())
                .createdAt(image.getCreatedAt())
                .build();
    }
}
