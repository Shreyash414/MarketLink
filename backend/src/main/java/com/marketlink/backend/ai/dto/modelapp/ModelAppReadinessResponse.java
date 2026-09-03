package com.marketlink.backend.ai.dto.modelapp;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * DTO matching Model-app ReadinessResponse schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppReadinessResponse {
    private Boolean ready;
    private String status;
    private Map<String, Object> dependencies;
    private String timestamp;
}
