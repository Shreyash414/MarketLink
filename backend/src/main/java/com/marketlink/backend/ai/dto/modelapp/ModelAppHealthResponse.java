package com.marketlink.backend.ai.dto.modelapp;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * DTO matching Model-app HealthResponse schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppHealthResponse {
    private String status;
    private String service;
    private String version;
    private String timestamp;
}
