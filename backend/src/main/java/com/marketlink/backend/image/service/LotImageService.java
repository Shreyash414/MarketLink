package com.marketlink.backend.image.service;

import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.image.entity.LotImage;
import com.marketlink.backend.domain.image.enums.ImageProcessingStatus;
import com.marketlink.backend.domain.image.repository.LotImageRepository;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.image.dto.LotImageResponse;
import com.marketlink.backend.image.dto.ProcessedImageResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.bson.BsonBinarySubType;
import org.bson.types.Binary;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class LotImageService {

    private final LotImageRepository lotImageRepository;
    private final LotRepository lotRepository;
    private final ImageProcessingService imageProcessingService;

    @Transactional
    public LotImageResponse uploadLotImage(UUID farmerId, UUID lotId, MultipartFile file, String imageType) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + lotId));

        if (!lot.getFarmerId().equals(farmerId)) {
            throw new ApiException("Not authorized to upload images for this lot", HttpStatus.FORBIDDEN);
        }

        if (lot.getStatus() == LotStatus.CLOSED || lot.getStatus() == LotStatus.CANCELLED) {
            throw new ApiException("Cannot upload images for closed or cancelled lots", HttpStatus.BAD_REQUEST);
        }

        ProcessedImageResult result = imageProcessingService.processImage(file);

        String originalFilename = file.getOriginalFilename() != null ? file.getOriginalFilename() : "photo.jpg";
        String type = (imageType != null && !imageType.isBlank()) ? imageType.trim().toUpperCase() : "PRODUCE_PHOTO";

        Binary bsonBinary = new Binary(BsonBinarySubType.BINARY, result.getData());

        LotImage image = LotImage.builder()
                .id(UUID.randomUUID())
                .lotId(lotId)
                .imageData(bsonBinary)
                .originalFilename(originalFilename)
                .contentType(result.getContentType())
                .fileSize(result.getFileSize())
                .width(result.getWidth())
                .height(result.getHeight())
                .imageType(type)
                .processingStatus(ImageProcessingStatus.PROCESSED)
                .createdAt(Instant.now())
                .updatedAt(Instant.now())
                .build();

        LotImage savedImage = lotImageRepository.save(image);
        log.info("Saved compressed BSON Binary image record in MongoDB: id={}, lotId={}, size={} bytes, dimensions={}x{}",
                savedImage.getId(), lotId, savedImage.getFileSize(), savedImage.getWidth(), savedImage.getHeight());

        return LotImageResponse.fromEntity(savedImage);
    }

    public LotImage getImageEntity(UUID lotId, UUID imageId) {
        return lotImageRepository.findByIdAndLotId(imageId, lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Image not found with id: " + imageId + " for lot: " + lotId));
    }

    public List<LotImageResponse> getLotImages(UUID lotId) {
        if (!lotRepository.existsById(lotId)) {
            throw new ResourceNotFoundException("Lot not found with id: " + lotId);
        }
        return lotImageRepository.findByLotIdOrderByCreatedAtDesc(lotId).stream()
                .map(LotImageResponse::fromEntity)
                .collect(Collectors.toList());
    }

    @Transactional
    public void deleteLotImage(UUID farmerId, UUID lotId, UUID imageId) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + lotId));

        if (!lot.getFarmerId().equals(farmerId)) {
            throw new ApiException("Not authorized to delete images from this lot", HttpStatus.FORBIDDEN);
        }

        LotImage image = lotImageRepository.findByIdAndLotId(imageId, lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Image not found with id: " + imageId));

        lotImageRepository.deleteByIdAndLotId(imageId, lotId);
        log.info("Deleted MongoDB image record: id={} from lot: {}", imageId, lotId);
    }
}
