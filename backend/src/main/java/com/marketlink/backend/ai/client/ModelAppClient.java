package com.marketlink.backend.ai.client;

import com.marketlink.backend.ai.dto.modelapp.*;

/**
 * Dedicated client interface for communication with the FastAPI Model-app.
 * Decouples Core Backend business services from direct HTTP implementation details.
 */
public interface ModelAppClient {

    /**
     * Checks Model-app process liveness.
     *
     * @return HealthResponse from Model-app
     */
    ModelAppHealthResponse checkHealth();

    /**
     * Checks external dependency readiness of Model-app (Redis, RabbitMQ, ML Predictor).
     *
     * @return ReadinessResponse from Model-app
     */
    ModelAppReadinessResponse checkReadiness();

    /**
     * Calls Model-app price prediction endpoint.
     *
     * @param request Model-app prediction parameters
     * @return Price prediction response
     */
    ModelAppPredictionResponse predictPrice(ModelAppPredictionRequest request);

    /**
     * Calls Model-app synchronous mandi recommendation endpoint.
     *
     * @param request Farmer location and commodity parameters
     * @return Comprehensive mandi ranking and financial response
     */
    ModelAppRecommendationResponse getRecommendation(ModelAppRecommendationRequest request);

    /**
     * Submits an asynchronous mandi recommendation job to Model-app.
     *
     * @param request Farmer location and commodity parameters
     * @return HTTP 202 Accepted response containing job_id and poll_url
     */
    ModelAppAsyncJobAcceptedResponse submitAsyncRecommendation(ModelAppRecommendationRequest request);

    /**
     * Retrieves current status and result for an asynchronous job.
     *
     * @param jobId UUID of the async job
     * @return Current job state (QUEUED, PROCESSING, COMPLETED, FAILED) and result
     */
    ModelAppJobStatusResponse getJobStatus(String jobId);

    /**
     * Dispatches a natural language farmer advisory query to Model-app (Ollama LLM).
     *
     * @param request Query text and language
     * @return Parsed trade intent and natural language advisory response
     */
    ModelAppQueryResponse processGeneralQuery(ModelAppQueryRequest request);

    /**
     * Retrieves current mandi modal prices and arrivals for a commodity from Model-app market-data API.
     *
     * @param commodity Commodity name (e.g. Onion, Potato, Tomato, Wheat, Rice)
     * @param markets   Optional target market names filter
     * @param state     Optional state name filter
     * @param limit     Max records to retrieve
     * @return MarketDataResponse from Model-app
     */
    ModelAppMarketDataResponse getMarketData(String commodity, java.util.List<String> markets, String state, Integer limit);
}
