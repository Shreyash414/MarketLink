package com.marketlink.backend.ai.enums;

/**
 * Strongly-typed enumeration of farmer AI query intents for intelligent capability routing.
 */
public enum AiQueryIntent {

    /**
     * General agricultural agronomy, crop storage, fertilizer, disease, cultivation advice (routed to Ollama LLM).
     */
    GENERAL_ADVISORY,

    /**
     * Factual current/today's mandi price and arrival inquiries (routed to AGMARKNET / Market Data API).
     */
    MARKET_DATA,

    /**
     * Future price forecasts, expected trends, next-day/week price estimates (routed to ML ModelPredictor).
     */
    PRICE_PREDICTION,

    /**
     * Best market selection, where to sell, net return comparisons (routed to MandiRecommender).
     */
    MANDI_RECOMMENDATION,

    /**
     * Multi-capability analytical query requiring both future price forecasting and mandi recommendation.
     */
    COMBINED_ANALYSIS
}
