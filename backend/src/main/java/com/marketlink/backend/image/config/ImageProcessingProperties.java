package com.marketlink.backend.image.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Getter
@Setter
@Configuration
@ConfigurationProperties(prefix = "marketlink.image")
public class ImageProcessingProperties {

    /**
     * Maximum allowed width for compressed images (default 1600px)
     */
    private int maxWidth = 1600;

    /**
     * Maximum allowed height for compressed images (default 1600px)
     */
    private int maxHeight = 1600;

    /**
     * JPEG compression quality factor between 0.0 and 1.0 (default 0.75)
     */
    private float jpegQuality = 0.75f;

    /**
     * Maximum final compressed binary size in bytes (default 5MB)
     */
    private long maxStoredSize = 5_000_000L;

    public long getMaxSizeBytes() {
        return maxStoredSize;
    }

    public void setMaxSizeBytes(long maxSizeBytes) {
        this.maxStoredSize = maxSizeBytes;
    }
}
