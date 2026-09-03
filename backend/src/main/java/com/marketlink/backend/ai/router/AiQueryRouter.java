package com.marketlink.backend.ai.router;

import com.marketlink.backend.ai.classifier.AiQueryClassifier;
import com.marketlink.backend.ai.client.ModelAppClient;
import com.marketlink.backend.ai.dto.modelapp.*;
import com.marketlink.backend.ai.dto.query.AiNaturalLanguageQueryRequest;
import com.marketlink.backend.ai.dto.query.AiQueryResponse;
import com.marketlink.backend.ai.enums.AiQueryIntent;
import com.marketlink.backend.ai.exception.ModelAppValidationException;
import com.marketlink.backend.domain.common.entity.Location;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;
import java.util.Locale;

/**
 * Orchestrates multi-capability routing of farmer AI queries to the appropriate engine in Model-app.
 * Dispatches queries to Ollama, Market Data, ML Price Prediction, Mandi Recommendation, or Combined workflows.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AiQueryRouter {

    private final AiQueryClassifier classifier;
    private final ModelAppClient modelAppClient;

    /**
     * Classifies the query and executes the appropriate capability workflow.
     */
    public AiQueryResponse route(AiNaturalLanguageQueryRequest request) {
        AiQueryClassifier.ClassificationResult classification = classifier.classify(request);
        AiQueryIntent intent = classification.getIntent();
        log.info("Query '{}' classified as intent='{}' (confidence={})",
                request.getQuery(), intent, classification.getConfidence());

        return switch (intent) {
            case GENERAL_ADVISORY -> handleGeneralAdvisory(request, classification);
            case MARKET_DATA -> handleMarketData(request, classification);
            case PRICE_PREDICTION -> handlePricePrediction(request, classification);
            case MANDI_RECOMMENDATION -> handleMandiRecommendation(request, classification);
            case COMBINED_ANALYSIS -> handleCombinedAnalysis(request, classification);
        };
    }

    private AiQueryResponse handleGeneralAdvisory(AiNaturalLanguageQueryRequest request,
                                                  AiQueryClassifier.ClassificationResult classification) {
        ModelAppQueryRequest queryReq = ModelAppQueryRequest.builder()
                .query(request.getQuery())
                .language(request.getLanguage() != null ? request.getLanguage() : "en")
                .build();

        ModelAppQueryResponse response = modelAppClient.processGeneralQuery(queryReq);
        return AiQueryResponse.builder()
                .intent(AiQueryIntent.GENERAL_ADVISORY)
                .confidence(classification.getConfidence())
                .answer(response.getResponse())
                .generalAdvisory(response)
                .timestamp(Instant.now())
                .build();
    }

    private AiQueryResponse handleMarketData(AiNaturalLanguageQueryRequest request,
                                             AiQueryClassifier.ClassificationResult classification) {
        String commodity = classification.getExtractedCommodity();
        String market = classification.getExtractedMarket();
        List<String> markets = market != null ? List.of(market) : null;

        ModelAppMarketDataResponse marketData = modelAppClient.getMarketData(commodity, markets, null, 20);

        String answer;
        if (marketData != null && marketData.getRecords() != null && !marketData.getRecords().isEmpty()) {
            ModelAppMandiPriceRecord first = marketData.getRecords().get(0);
            answer = String.format(Locale.ROOT,
                    "Current modal price for %s in %s (%s) is ₹%.1f/quintal (Date: %s, Source: %s).",
                    first.getCommodity(), first.getMarket(), first.getState(),
                    first.getModalPrice(), first.getDate(), marketData.getDataSource());
        } else {
            answer = String.format(Locale.ROOT,
                    "No recent market price observations found for %s in %s.",
                    commodity, market != null ? market : "specified mandis");
        }

        return AiQueryResponse.builder()
                .intent(AiQueryIntent.MARKET_DATA)
                .confidence(classification.getConfidence())
                .answer(answer)
                .marketData(marketData)
                .timestamp(Instant.now())
                .build();
    }

    private AiQueryResponse handlePricePrediction(AiNaturalLanguageQueryRequest request,
                                                  AiQueryClassifier.ClassificationResult classification) {
        String commodity = classification.getExtractedCommodity();
        String market = classification.getExtractedMarket() != null ? classification.getExtractedMarket() : "Bareilly";
        double currentPrice = request.getCurrentPrice() != null && request.getCurrentPrice() > 0
                ? request.getCurrentPrice()
                : 1850.0;

        ModelAppPredictionRequest predReq = ModelAppPredictionRequest.builder()
                .market(market)
                .commodity(commodity)
                .currentPrice(currentPrice)
                .farmerFacing(true)
                .build();

        ModelAppPredictionResponse prediction = modelAppClient.predictPrice(predReq);

        String answer = String.format(Locale.ROOT,
                "Next-day forecasted price for %s in %s is ₹%.1f/quintal (Expected change: %s₹%.1f, %s). Model reliability: %s (Score: %.1f%%).",
                prediction.getCommodity(), prediction.getMarket(), prediction.getPredictedPrice(),
                prediction.getExpectedChange() >= 0 ? "+" : "", prediction.getExpectedChange(),
                prediction.getExpectedDirection(), prediction.getQualityClass(), prediction.getReliabilityScore());

        return AiQueryResponse.builder()
                .intent(AiQueryIntent.PRICE_PREDICTION)
                .confidence(classification.getConfidence())
                .answer(answer)
                .prediction(prediction)
                .timestamp(Instant.now())
                .build();
    }

    private AiQueryResponse handleMandiRecommendation(AiNaturalLanguageQueryRequest request,
                                                      AiQueryClassifier.ClassificationResult classification) {
        Location loc = request.getLocation();
        if (loc == null || loc.getLatitude() == null || loc.getLongitude() == null) {
            throw new ModelAppValidationException(
                    "Farmer location coordinates (latitude and longitude) are required for mandi recommendations"
            );
        }

        ModelAppRecommendationRequest recReq = ModelAppRecommendationRequest.builder()
                .farmerLatitude(loc.getLatitude())
                .farmerLongitude(loc.getLongitude())
                .quantityQuintals(request.resolveQuantityQuintals())
                .commodity(classification.getExtractedCommodity())
                .maxDistanceKm(request.getMaxDistanceKm())
                .topN(5)
                .build();

        ModelAppRecommendationResponse recommendation = modelAppClient.getRecommendation(recReq);

        String answer;
        if (recommendation.getRecommendations() != null && !recommendation.getRecommendations().isEmpty()) {
            ModelAppMandiItem top = recommendation.getRecommendations().get(0);
            answer = String.format(Locale.ROOT,
                    "Recommended mandi: %s (%s, %.1f km away) with estimated net return of ₹%.1f for %.1f quintals of %s.",
                    top.getMandi(), top.getState(), top.getDistanceKm(),
                    top.getNetReturn() != null ? top.getNetReturn() : 0.0,
                    recReq.getQuantityQuintals(), recommendation.getCommodity());
        } else {
            answer = String.format(Locale.ROOT,
                    "No eligible mandis found within search radius for %s.",
                    recommendation.getCommodity());
        }

        return AiQueryResponse.builder()
                .intent(AiQueryIntent.MANDI_RECOMMENDATION)
                .confidence(classification.getConfidence())
                .answer(answer)
                .recommendation(recommendation)
                .timestamp(Instant.now())
                .build();
    }

    private AiQueryResponse handleCombinedAnalysis(AiNaturalLanguageQueryRequest request,
                                                   AiQueryClassifier.ClassificationResult classification) {
        String commodity = classification.getExtractedCommodity();
        String market = classification.getExtractedMarket() != null ? classification.getExtractedMarket() : "Bareilly";
        double currentPrice = request.getCurrentPrice() != null && request.getCurrentPrice() > 0
                ? request.getCurrentPrice()
                : 1850.0;

        // 1. Call Price Prediction
        ModelAppPredictionRequest predReq = ModelAppPredictionRequest.builder()
                .market(market)
                .commodity(commodity)
                .currentPrice(currentPrice)
                .farmerFacing(true)
                .build();
        ModelAppPredictionResponse prediction = modelAppClient.predictPrice(predReq);

        // 2. Call Mandi Recommendation (if location available; fallback to default if test location)
        ModelAppRecommendationResponse recommendation = null;
        Location loc = request.getLocation();
        if (loc != null && loc.getLatitude() != null && loc.getLongitude() != null) {
            ModelAppRecommendationRequest recReq = ModelAppRecommendationRequest.builder()
                    .farmerLatitude(loc.getLatitude())
                    .farmerLongitude(loc.getLongitude())
                    .quantityQuintals(request.resolveQuantityQuintals())
                    .commodity(commodity)
                    .maxDistanceKm(request.getMaxDistanceKm())
                    .topN(5)
                    .build();
            recommendation = modelAppClient.getRecommendation(recReq);
        }

        String answer;
        if (recommendation != null && recommendation.getRecommendations() != null && !recommendation.getRecommendations().isEmpty()) {
            ModelAppMandiItem top = recommendation.getRecommendations().get(0);
            answer = String.format(Locale.ROOT,
                    "Combined Analysis: Selling in %s yields highest estimated net return of ₹%.1f. Next-day prices are projected to trend %s to ₹%.1f/quintal.",
                    top.getMandi(), top.getNetReturn() != null ? top.getNetReturn() : 0.0,
                    prediction.getExpectedDirection(), prediction.getPredictedPrice());
        } else {
            answer = String.format(Locale.ROOT,
                    "Price Forecast: %s in %s is projected to trend %s to ₹%.1f/quintal.",
                    commodity, market, prediction.getExpectedDirection(), prediction.getPredictedPrice());
        }

        String explanation = String.format(Locale.ROOT,
                "Analytical synthesis combining ML price forecasting in %s with geospatial mandi ranking for %s.",
                market, commodity);

        return AiQueryResponse.builder()
                .intent(AiQueryIntent.COMBINED_ANALYSIS)
                .confidence(classification.getConfidence())
                .answer(answer)
                .prediction(prediction)
                .recommendation(recommendation)
                .explanation(explanation)
                .timestamp(Instant.now())
                .build();
    }
}
