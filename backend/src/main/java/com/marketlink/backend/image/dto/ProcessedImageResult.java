package com.marketlink.backend.image.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProcessedImageResult {
    private byte[] data;
    private int width;
    private int height;
    private long fileSize;
    private String contentType;
}
