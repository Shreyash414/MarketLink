package com.marketlink.backend.ai.dto.modelapp;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * DTO matching Model-app GeneralQueryResponse schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppQueryResponse {

    private String query;
    private String intent;
    private Map<String, Object> entities;
    private String response;
    private String language;
    private Double confidence;
    private String source;
    private String model;
    private String timestamp;
}
