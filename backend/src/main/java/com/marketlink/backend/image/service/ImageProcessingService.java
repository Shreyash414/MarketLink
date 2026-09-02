package com.marketlink.backend.image.service;

import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.image.config.ImageProcessingProperties;
import com.marketlink.backend.image.dto.ProcessedImageResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import javax.imageio.IIOImage;
import javax.imageio.ImageIO;
import javax.imageio.ImageWriteParam;
import javax.imageio.ImageWriter;
import javax.imageio.stream.ImageOutputStream;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.Iterator;

@Slf4j
@Service
@RequiredArgsConstructor
public class ImageProcessingService {

    private final ImageProcessingProperties properties;

    public ProcessedImageResult processImage(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new ApiException("Image file cannot be empty", HttpStatus.BAD_REQUEST);
        }

        BufferedImage originalImage = validateAndReadImage(file);
        int targetWidth = properties.getMaxWidth();
        int targetHeight = properties.getMaxHeight();
        float quality = properties.getJpegQuality();

        BufferedImage resizedImage = resizePreservingAspectRatio(originalImage, targetWidth, targetHeight);
        byte[] compressedBytes = compressToJpeg(resizedImage, quality);

        // Final size protection: downscale more if resulting image exceeds configured maximum
        int currentWidth = resizedImage.getWidth();
        int currentHeight = resizedImage.getHeight();
        int iteration = 0;

        while (compressedBytes.length > properties.getMaxSizeBytes() && iteration < 3) {
            iteration++;
            log.warn("Compressed image size ({} bytes) exceeds maximum ({} bytes), reducing dimensions (pass {})",
                    compressedBytes.length, properties.getMaxSizeBytes(), iteration);
            currentWidth = (int) (currentWidth * 0.75);
            currentHeight = (int) (currentHeight * 0.75);
            quality = Math.max(0.5f, quality - 0.1f);

            resizedImage = resizePreservingAspectRatio(originalImage, currentWidth, currentHeight);
            compressedBytes = compressToJpeg(resizedImage, quality);
        }

        if (compressedBytes.length > properties.getMaxSizeBytes()) {
            throw new ApiException("Image is too large and cannot be compressed within acceptable limits", HttpStatus.BAD_REQUEST);
        }

        log.info("Processed and compressed image: originalSize={}, finalSize={}, finalDimensions={}x{}",
                file.getSize(), compressedBytes.length, resizedImage.getWidth(), resizedImage.getHeight());

        return ProcessedImageResult.builder()
                .data(compressedBytes)
                .width(resizedImage.getWidth())
                .height(resizedImage.getHeight())
                .fileSize((long) compressedBytes.length)
                .contentType("image/jpeg")
                .build();
    }

    public BufferedImage validateAndReadImage(MultipartFile file) {
        try {
            BufferedImage image = ImageIO.read(file.getInputStream());
            if (image == null) {
                throw new ApiException("Uploaded file is not a valid image format (supported: JPEG, PNG, WEBP, BMP)", HttpStatus.BAD_REQUEST);
            }
            return image;
        } catch (IOException e) {
            log.error("Failed to read image stream: {}", e.getMessage());
            throw new ApiException("Failed to decode uploaded image: " + e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }

    public BufferedImage resizePreservingAspectRatio(BufferedImage originalImage, int maxWidth, int maxHeight) {
        int origWidth = originalImage.getWidth();
        int origHeight = originalImage.getHeight();

        // Do not upscale if image is already within target bounds
        if (origWidth <= maxWidth && origHeight <= maxHeight) {
            // Convert to RGB if needed (handles RGBA / PNG transparency)
            if (originalImage.getType() == BufferedImage.TYPE_INT_RGB) {
                return originalImage;
            }
            BufferedImage rgbImage = new BufferedImage(origWidth, origHeight, BufferedImage.TYPE_INT_RGB);
            Graphics2D g2d = rgbImage.createGraphics();
            g2d.setColor(Color.WHITE);
            g2d.fillRect(0, 0, origWidth, origHeight);
            g2d.drawImage(originalImage, 0, 0, null);
            g2d.dispose();
            return rgbImage;
        }

        // Calculate aspect ratio preserving scaling factor
        double scale = Math.min((double) maxWidth / origWidth, (double) maxHeight / origHeight);
        int targetWidth = Math.max(1, (int) (origWidth * scale));
        int targetHeight = Math.max(1, (int) (origHeight * scale));

        Image scaledImage = originalImage.getScaledInstance(targetWidth, targetHeight, Image.SCALE_SMOOTH);
        BufferedImage outputImage = new BufferedImage(targetWidth, targetHeight, BufferedImage.TYPE_INT_RGB);

        Graphics2D g2d = outputImage.createGraphics();
        g2d.setColor(Color.WHITE);
        g2d.fillRect(0, 0, targetWidth, targetHeight);
        g2d.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
        g2d.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_QUALITY);
        g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g2d.drawImage(scaledImage, 0, 0, null);
        g2d.dispose();

        return outputImage;
    }

    public byte[] compressToJpeg(BufferedImage image, float quality) {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        Iterator<ImageWriter> writers = ImageIO.getImageWritersByFormatName("jpg");

        if (!writers.hasNext()) {
            throw new IllegalStateException("No JPEG ImageWriter found in system runtime");
        }

        ImageWriter writer = writers.next();
        try (ImageOutputStream ios = ImageIO.createImageOutputStream(baos)) {
            writer.setOutput(ios);
            ImageWriteParam param = writer.getDefaultWriteParam();
            param.setCompressionMode(ImageWriteParam.MODE_EXPLICIT);
            param.setCompressionQuality(Math.max(0.0f, Math.min(1.0f, quality)));

            writer.write(null, new IIOImage(image, null, null), param);
        } catch (IOException e) {
            log.error("Error during JPEG compression: {}", e.getMessage());
            throw new ApiException("Image compression failed: " + e.getMessage(), HttpStatus.INTERNAL_SERVER_ERROR);
        } finally {
            writer.dispose();
        }

        return baos.toByteArray();
    }
}
