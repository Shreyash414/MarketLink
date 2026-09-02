package com.marketlink.backend.image;

import com.marketlink.backend.domain.image.entity.LotImage;
import com.marketlink.backend.domain.image.enums.ImageProcessingStatus;
import com.marketlink.backend.domain.image.repository.LotImageRepository;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.image.dto.LotImageResponse;
import com.marketlink.backend.image.service.LotImageService;
import org.bson.BsonBinarySubType;
import org.bson.types.Binary;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
class MongoLotImageStorageTest {

    @Autowired
    private LotImageRepository lotImageRepository;

    @Autowired
    private LotRepository lotRepository;

    @Autowired
    private LotImageService lotImageService;

    private UUID farmerId;
    private UUID lotId;
    private Lot sampleLot;

    @BeforeEach
    void setUp() {
        lotImageRepository.deleteAll();
        lotRepository.deleteAll();

        farmerId = UUID.randomUUID();

        sampleLot = lotRepository.save(Lot.builder()
                .farmerId(farmerId)
                .cropName("TOMATO")
                .quantity(1000.0)
                .expectedPrice(40.0)
                .status(LotStatus.DRAFT)
                .build());
        lotId = sampleLot.getId();
    }

    private byte[] createDummyJpegBytes() throws IOException {
        BufferedImage img = new BufferedImage(800, 600, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = img.createGraphics();
        g.setColor(Color.RED);
        g.fillRect(0, 0, 800, 600);
        g.dispose();

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(img, "jpg", baos);
        return baos.toByteArray();
    }

    @Test
    @DisplayName("Verify image is persisted in MongoDB as raw BSON Binary and NOT Base64")
    void testImageStoredAsBsonBinary() throws IOException {
        byte[] rawBytes = createDummyJpegBytes();
        MockMultipartFile file = new MockMultipartFile(
                "file", "tomato_sample.jpg", "image/jpeg", rawBytes);

        LotImageResponse response = lotImageService.uploadLotImage(farmerId, lotId, file, "PRODUCE_PHOTO");

        assertThat(response).isNotNull();
        assertThat(response.getId()).isNotNull();
        assertThat(response.getLotId()).isEqualTo(lotId);

        // Fetch direct document from MongoDB repository
        Optional<LotImage> docOpt = lotImageRepository.findById(response.getId());
        assertThat(docOpt).isPresent();

        LotImage doc = docOpt.get();
        assertThat(doc.getImageData()).isNotNull();
        assertThat(doc.getImageData()).isInstanceOf(Binary.class);
        assertThat(doc.getImageData().getType()).isEqualTo(BsonBinarySubType.BINARY.getValue());
        assertThat(doc.getImageData().getData()).isNotEmpty();

        // Verify stored binary is exact JPEG bytes without Base64 inflation
        byte[] storedBytes = doc.getImageData().getData();
        assertThat(storedBytes.length).isEqualTo(doc.getFileSize().intValue());
    }

    @Test
    @DisplayName("Verify lotId based queries and cross-lot isolation in MongoDB repository")
    void testCrossLotIsolation() throws IOException {
        UUID lotId2 = UUID.randomUUID();
        byte[] rawBytes = createDummyJpegBytes();

        LotImage img1 = lotImageRepository.save(LotImage.builder()
                .id(UUID.randomUUID())
                .lotId(lotId)
                .imageData(new Binary(BsonBinarySubType.BINARY, rawBytes))
                .originalFilename("lot1_photo.jpg")
                .contentType("image/jpeg")
                .fileSize((long) rawBytes.length)
                .imageType("PRODUCE_PHOTO")
                .processingStatus(ImageProcessingStatus.PROCESSED)
                .createdAt(Instant.now())
                .updatedAt(Instant.now())
                .build());

        // 1. Query by correct lotId -> found
        List<LotImage> lot1Images = lotImageRepository.findByLotId(lotId);
        assertThat(lot1Images).hasSize(1);
        assertThat(lot1Images.getFirst().getId()).isEqualTo(img1.getId());

        // 2. Query by different lotId -> empty
        List<LotImage> lot2Images = lotImageRepository.findByLotId(lotId2);
        assertThat(lot2Images).isEmpty();

        // 3. Query by wrong lotId with findByIdAndLotId -> empty
        Optional<LotImage> wrongLotLookup = lotImageRepository.findByIdAndLotId(img1.getId(), lotId2);
        assertThat(wrongLotLookup).isEmpty();

        // 4. Correct lookup
        Optional<LotImage> correctLookup = lotImageRepository.findByIdAndLotId(img1.getId(), lotId);
        assertThat(correctLookup).isPresent();
    }

    @Test
    @DisplayName("Verify deleteByIdAndLotId removes document from MongoDB")
    void testDeleteImageFromMongo() throws IOException {
        byte[] rawBytes = createDummyJpegBytes();

        LotImage img = lotImageRepository.save(LotImage.builder()
                .id(UUID.randomUUID())
                .lotId(lotId)
                .imageData(new Binary(BsonBinarySubType.BINARY, rawBytes))
                .originalFilename("to_delete.jpg")
                .contentType("image/jpeg")
                .fileSize((long) rawBytes.length)
                .imageType("PRODUCE_PHOTO")
                .processingStatus(ImageProcessingStatus.PROCESSED)
                .createdAt(Instant.now())
                .updatedAt(Instant.now())
                .build());

        lotImageService.deleteLotImage(farmerId, lotId, img.getId());

        assertThat(lotImageRepository.findById(img.getId())).isEmpty();
    }
}
