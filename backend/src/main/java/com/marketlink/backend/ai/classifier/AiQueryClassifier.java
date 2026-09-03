package com.marketlink.backend.ai.classifier;

import com.marketlink.backend.ai.dto.query.AiNaturalLanguageQueryRequest;
import com.marketlink.backend.ai.enums.AiQueryIntent;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * Deterministic rule-based intent classifier for farmer natural-language queries.
 * Identifies trade intent without adding external LLM latency or non-deterministic variance.
 */
@Slf4j
@Component
public class AiQueryClassifier {

    // Regex patterns for prediction / future forecasting concepts (English & Hinglish)
    private static final Pattern PREDICTION_PATTERN = Pattern.compile(
            "\\b(predict|prediction|forecast|future|next\\s+week|next\\s+month|tomorrow|expected\\s+price|future\\s+price|price\\s+estimate|what\\s+price\\s+can\\s+i\\s+expect|kya\\s+bhav\\s+milega|bhav\\s+milega|rate\\s+milega|aage\\s+ka\\s+bhav|aage\\s+ka\\s+rate)\\b",
            Pattern.CASE_INSENSITIVE
    );

    // Regex patterns for recommendation / market selection concepts (English & Hinglish)
    private static final Pattern RECOMMENDATION_PATTERN = Pattern.compile(
            "\\b(where\\s+should\\s+i\\s+sell|which\\s+mandi|which\\s+market|best\\s+mandi|best\\s+market|recommended\\s+mandi|recommend\\s+mandi|where\\s+can\\s+i\\s+get\\s+better\\s+price|where\\s+to\\s+sell|kahan\\s+bechun|kahan\\s+bechna|kaunsi\\s+mandi|sahi\\s+mandi|mandi\\s+suggest)\\b",
            Pattern.CASE_INSENSITIVE
    );

    // Regex patterns for current market price / spot data concepts (English & Hinglish)
    private static final Pattern MARKET_DATA_PATTERN = Pattern.compile(
            "\\b(today'?s?\\s+price|current\\s+price|market\\s+price|mandi\\s+price|latest\\s+price|what\\s+is\\s+the\\s+price|what\\s+is\\s+today|aaj\\s+ka\\s+bhav|aaj\\s+ka\\s+rate|bhav\\s+kya\\s+hai|rate\\s+kya\\s+hai|current\\s+rate|modal\\s+price)\\b",
            Pattern.CASE_INSENSITIVE
    );

    // Regex patterns for general agronomy / storage / cultivation advice
    private static final Pattern GENERAL_ADVISORY_PATTERN = Pattern.compile(
            "\\b(how\\s+to\\s+store|store|storage|cultivate|cultivation|fertilizer|prevent\\s+spoilage|spoilage|disease|pest|fungus|keede|khad|kheti|kheti\\s+badi|how\\s+to\\s+grow|irrigation|soil)\\b",
            Pattern.CASE_INSENSITIVE
    );

    @Data
    @Builder
    public static class ClassificationResult {
        private AiQueryIntent intent;
        private double confidence;
        private String extractedCommodity;
        private String extractedMarket;
        private List<String> matchReasons;
    }

    /**
     * Classifies farmer query deterministically based on keyword triggers and request metadata.
     *
     * @param request Incoming query and context
     * @return ClassificationResult containing intent and extracted entities
     */
    public ClassificationResult classify(AiNaturalLanguageQueryRequest request) {
        String rawQuery = request.getQuery() != null ? request.getQuery().trim() : "";
        String normalized = rawQuery.toLowerCase(Locale.ROOT);
        List<String> reasons = new ArrayList<>();

        String commodity = resolveOrExtractCommodity(request, normalized);
        String market = resolveOrExtractMarket(request, normalized);

        boolean hasPrediction = PREDICTION_PATTERN.matcher(normalized).find();
        boolean hasRecommendation = RECOMMENDATION_PATTERN.matcher(normalized).find();
        boolean hasMarketData = MARKET_DATA_PATTERN.matcher(normalized).find();
        boolean hasGeneral = GENERAL_ADVISORY_PATTERN.matcher(normalized).find();

        // 1. Check for Combined Analysis (Both future prediction and selling decision)
        if (hasPrediction && hasRecommendation) {
            reasons.add("Query matched both future prediction and mandi recommendation patterns");
            return ClassificationResult.builder()
                    .intent(AiQueryIntent.COMBINED_ANALYSIS)
                    .confidence(0.95)
                    .extractedCommodity(commodity)
                    .extractedMarket(market)
                    .matchReasons(reasons)
                    .build();
        }

        // 2. Mandi Recommendation
        if (hasRecommendation) {
            reasons.add("Query matched mandi recommendation pattern");
            return ClassificationResult.builder()
                    .intent(AiQueryIntent.MANDI_RECOMMENDATION)
                    .confidence(0.92)
                    .extractedCommodity(commodity)
                    .extractedMarket(market)
                    .matchReasons(reasons)
                    .build();
        }

        // 3. Price Prediction (e.g. next week, tomorrow, forecast)
        if (hasPrediction) {
            reasons.add("Query matched future price forecast pattern");
            return ClassificationResult.builder()
                    .intent(AiQueryIntent.PRICE_PREDICTION)
                    .confidence(0.90)
                    .extractedCommodity(commodity)
                    .extractedMarket(market)
                    .matchReasons(reasons)
                    .build();
        }

        // 4. Current Market Data (e.g. today's price, mandi rate)
        if (hasMarketData) {
            reasons.add("Query matched spot market data pattern");
            return ClassificationResult.builder()
                    .intent(AiQueryIntent.MARKET_DATA)
                    .confidence(0.90)
                    .extractedCommodity(commodity)
                    .extractedMarket(market)
                    .matchReasons(reasons)
                    .build();
        }

        // 5. Agronomy / Cultivation / Storage guidance
        if (hasGeneral) {
            reasons.add("Query matched agricultural advisory / storage pattern");
            return ClassificationResult.builder()
                    .intent(AiQueryIntent.GENERAL_ADVISORY)
                    .confidence(0.88)
                    .extractedCommodity(commodity)
                    .extractedMarket(market)
                    .matchReasons(reasons)
                    .build();
        }

        // 6. Contextual heuristics: If market or price is mentioned with a commodity
        if (normalized.contains("price") || normalized.contains("rate") || normalized.contains("bhav")) {
            reasons.add("Query contains price terminology without future indicators; classifying as spot market data");
            return ClassificationResult.builder()
                    .intent(AiQueryIntent.MARKET_DATA)
                    .confidence(0.75)
                    .extractedCommodity(commodity)
                    .extractedMarket(market)
                    .matchReasons(reasons)
                    .build();
        }

        // 7. Fallback to General Advisory (Ollama LLM)
        reasons.add("No specific ML or market data trigger identified; defaulting to general advisory");
        return ClassificationResult.builder()
                .intent(AiQueryIntent.GENERAL_ADVISORY)
                .confidence(0.65)
                .extractedCommodity(commodity)
                .extractedMarket(market)
                .matchReasons(reasons)
                .build();
    }

    private String resolveOrExtractCommodity(AiNaturalLanguageQueryRequest request, String normalized) {
        if (request.getCrop() != null && !request.getCrop().isBlank()) {
            return request.getCrop().trim();
        }
        if (normalized.contains("onion") || normalized.contains("pyaj") || normalized.contains("pyaaz")) {
            return "Onion";
        }
        if (normalized.contains("potato") || normalized.contains("aloo")) {
            return "Potato";
        }
        if (normalized.contains("tomato") || normalized.contains("tamatar")) {
            return "Tomato";
        }
        if (normalized.contains("wheat") || normalized.contains("gehu") || normalized.contains("gehun")) {
            return "Wheat";
        }
        if (normalized.contains("rice") || normalized.contains("chawal") || normalized.contains("dhan")) {
            return "Rice";
        }
        return "Onion";
    }

    private String resolveOrExtractMarket(AiNaturalLanguageQueryRequest request, String normalized) {
        if (request.getMarket() != null && !request.getMarket().isBlank()) {
            return request.getMarket().trim();
        }
        String[] knownMarkets = {"bareilly", "nagpur", "agra", "kolar", "khanna", "indore", "burdwan", "bargarh", "nashik", "pune", "delhi", "azadpur"};
        for (String m : knownMarkets) {
            if (normalized.contains(m)) {
                // Return capitalized version
                return Character.toUpperCase(m.charAt(0)) + m.substring(1);
            }
        }
        return null;
    }
}
