package com.marketlink.backend.image;

import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.image.config.ImageProcessingProperties;
import com.marketlink.backend.image.dto.ProcessedImageResult;
import com.marketlink.backend.image.service.ImageProcessingService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ImageProcessingServiceTest {

    private ImageProcessingService imageProcessingService;
    private ImageProcessingProperties properties;

    @BeforeEach
    void setUp() {
        properties = new ImageProcessingProperties();
        properties.setMaxWidth(800);
        properties.setMaxHeight(800);
        properties.setJpegQuality(0.75f);
        properties.setMaxSizeBytes(1024 * 1024L);

        imageProcessingService = new ImageProcessingService(properties);
    }

    private byte[] createTestImageBytes(int width, int height, String format) throws IOException {
        BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        Graphics2D g2d = image.createGraphics();
        g2d.setColor(Color.RED);
        g2d.fillRect(0, 0, width, height);
        g2d.setColor(Color.BLUE);
        g2d.drawLine(0, 0, width, height);
        g2d.dispose();

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(image, format, baos);
        return baos.toByteArray();
    }

    @Test
    @DisplayName("Downscale large image preserving aspect ratio (1600x1200 -> 800x600)")
    void testProcessImage_DownscalePreservesAspectRatio() throws IOException {
        byte[] largeImageBytes = createTestImageBytes(1600, 1200, "png");
        MockMultipartFile file = new MockMultipartFile(
                "file", "harvest.png", "image/png", largeImageBytes);

        ProcessedImageResult result = imageProcessingService.processImage(file);

        assertThat(result).isNotNull();
        assertThat(result.getWidth()).isEqualTo(800);
        assertThat(result.getHeight()).isEqualTo(600);
        assertThat(result.getContentType()).isEqualTo("image/jpeg");
        assertThat(result.getData()).isNotEmpty();
        assertThat(result.getFileSize()).isLessThanOrEqualTo(properties.getMaxSizeBytes());
    }

    @Test
    @DisplayName("Do not upscale smaller image (400x300 remains 400x300)")
    void testProcessImage_DoNotUpscaleSmallImage() throws IOException {
        byte[] smallImageBytes = createTestImageBytes(400, 300, "jpg");
        MockMultipartFile file = new MockMultipartFile(
                "file", "small.jpg", "image/jpeg", smallImageBytes);

        ProcessedImageResult result = imageProcessingService.processImage(file);

        assertThat(result).isNotNull();
        assertThat(result.getWidth()).isEqualTo(400);
        assertThat(result.getHeight()).isEqualTo(300);
        assertThat(result.getContentType()).isEqualTo("image/jpeg");
    }

    @Test
    @DisplayName("Reject non-image or invalid bytes with ApiException")
    void testProcessImage_InvalidFile() {
        byte[] fakeBytes = "This is definitely not an image".getBytes();
        MockMultipartFile file = new MockMultipartFile(
                "file", "corrupt.txt", "text/plain", fakeBytes);

        assertThatThrownBy(() -> imageProcessingService.processImage(file))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("not a valid image format");
    }

    @Test
    @DisplayName("Reject empty upload")
    void testProcessImage_EmptyFile() {
        MockMultipartFile emptyFile = new MockMultipartFile(
                "file", "empty.jpg", "image/jpeg", new byte[0]);

        assertThatThrownBy(() -> imageProcessingService.processImage(emptyFile))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("cannot be empty");
    }
}
