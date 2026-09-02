package com.marketlink.backend.domain.image.entity;

import com.marketlink.backend.domain.image.enums.ImageProcessingStatus;
import lombok.*;
import org.bson.types.Binary;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;
import java.util.UUID;

@Document(collection = "lot_images")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class LotImage {

    @Id
    private UUID id;

    @Indexed
    @Field("lot_id")
    private UUID lotId;

    @Field("image_data")
    private Binary imageData;

    @Field("original_filename")
    private String originalFilename;

    @Field("content_type")
    @Builder.Default
    private String contentType = "image/jpeg";

    @Field("file_size")
    private Long fileSize;

    @Field("width")
    private Integer width;

    @Field("height")
    private Integer height;

    @Field("image_type")
    @Builder.Default
    private String imageType = "PRODUCE_PHOTO";

    @Field("processing_status")
    @Builder.Default
    private ImageProcessingStatus processingStatus = ImageProcessingStatus.PROCESSED;

    @CreatedDate
    @Field("created_at")
    private Instant createdAt;

    @LastModifiedDate
    @Field("updated_at")
    private Instant updatedAt;
}
