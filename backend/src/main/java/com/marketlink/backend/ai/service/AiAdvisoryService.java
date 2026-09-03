package com.marketlink.backend.ai.service;

import com.marketlink.backend.ai.client.ModelAppClient;
import com.marketlink.backend.ai.dto.modelapp.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * Core Backend service orchestrating AI/ML capabilities by delegating to the ModelAppClient.
 * Enforces SOLID separation between business services and HTTP client communication.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AiAdvisoryService {

    private final ModelAppClient modelAppClient;
    private final com.marketlink.backend.ai.router.AiQueryRouter aiQueryRouter;

    /**
     * Routes incoming farmer natural language queries dynamically to the appropriate AI/ML or LLM capability.
     */
    public com.marketlink.backend.ai.dto.query.AiQueryResponse routeNaturalLanguageQuery(
            com.marketlink.backend.ai.dto.query.AiNaturalLanguageQueryRequest request) {
        return aiQueryRouter.route(request);
    }

    /**
     * Obtains next-day price forecast for a commodity in a given mandi.
     */
    public ModelAppPredictionResponse predictPrice(ModelAppPredictionRequest request) {
        log.info("Processing price prediction request for commodity '{}' in market '{}'",
                request.getCommodity(), request.getMarket());
        return modelAppClient.predictPrice(request);
    }

    /**
     * Obtains synchronous mandi rankings and net return calculations.
     */
    public ModelAppRecommendationResponse getMandiRecommendation(ModelAppRecommendationRequest request) {
        log.info("Processing synchronous recommendation for commodity '{}' at coordinates ({}, {})",
                request.getCommodity(), request.getFarmerLatitude(), request.getFarmerLongitude());
        return modelAppClient.getRecommendation(request);
    }

    /**
     * Submits an asynchronous recommendation job to be processed by background workers.
     */
    public ModelAppAsyncJobAcceptedResponse submitAsyncRecommendation(ModelAppRecommendationRequest request) {
        log.info("Submitting async recommendation job for commodity '{}'", request.getCommodity());
        return modelAppClient.submitAsyncRecommendation(request);
    }

    /**
     * Polls the current state of an asynchronous AI job.
     */
    public ModelAppJobStatusResponse getJobStatus(String jobId) {
        return modelAppClient.getJobStatus(jobId);
    }

    /**
     * Dispatches natural language trade advisory queries to the Ollama LLM via Model-app.
     */
    public ModelAppQueryResponse processGeneralQuery(ModelAppQueryRequest request) {
        log.info("Processing farmer natural language query");
        return modelAppClient.processGeneralQuery(request);
    }

    /**
     * Verifies Model-app process health.
     */
    public ModelAppHealthResponse checkHealth() {
        return modelAppClient.checkHealth();
    }

    /**
     * Verifies Model-app infrastructure readiness.
     */
    public ModelAppReadinessResponse checkReadiness() {
        return modelAppClient.checkReadiness();
    }
}
