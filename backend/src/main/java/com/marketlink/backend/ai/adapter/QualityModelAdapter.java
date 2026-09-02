package com.marketlink.backend.ai.adapter;

import com.marketlink.backend.domain.quality.entity.QualityAnalysisResult;

import java.util.UUID;

/**
 * Model-agnostic adapter interface for decoupling AI/ML model output formats
 * from MarketLink's core domain layer.
 */
public interface QualityModelAdapter {

    /**
     * Determines if this adapter handles the specific model provider or payload format.
     */
    boolean supports(String modelProvider);

    /**
     * Converts raw external model response payload into MarketLink's standardized QualityAnalysisResult domain entity.
     */
    QualityAnalysisResult adapt(UUID lotId, Object rawModelOutput);
}
