package com.marketlink.backend.ai.controller;

import com.marketlink.backend.ai.dto.modelapp.*;
import com.marketlink.backend.ai.service.AiAdvisoryService;
import com.marketlink.backend.common.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * Controller exposing AI advisory, price prediction, mandi recommendation, and async job APIs.
 */
@RestController
@RequestMapping("/api/v1/ai")
@RequiredArgsConstructor
@Tag(name = "AI Advisory & Recommendations", description = "AI-driven price forecasting, mandi recommendations, and farmer advisory")
public class AiAdvisoryController {

    private final AiAdvisoryService aiAdvisoryService;

    @PostMapping("/predict")
    @Operation(summary = "Forecast produce price", description = "Forecasts next-day modal price for a commodity in a specific market using XGBoost models",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Price forecast generated successfully",
                    content = @Content(schema = @Schema(implementation = ModelAppPredictionResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "Invalid prediction parameters"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "Market or model not found"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "503", description = "AI model service unavailable")
    })
    public ResponseEntity<ApiResponse<ModelAppPredictionResponse>> predictPrice(
            @Valid @RequestBody ModelAppPredictionRequest request) {
        ModelAppPredictionResponse response = aiAdvisoryService.predictPrice(request);
        return ResponseEntity.ok(ApiResponse.success("Price forecast generated successfully", response));
    }

    @PostMapping("/recommend")
    @Operation(summary = "Synchronous mandi recommendation", description = "Computes ranked mandi recommendations with net returns for farmer produce and location",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Mandi recommendations generated successfully",
                    content = @Content(schema = @Schema(implementation = ModelAppRecommendationResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "Invalid coordinates or quantity"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "422", description = "Validation error"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "503", description = "Recommendation engine unavailable")
    })
    public ResponseEntity<ApiResponse<ModelAppRecommendationResponse>> getRecommendation(
            @Valid @RequestBody ModelAppRecommendationRequest request) {
        ModelAppRecommendationResponse response = aiAdvisoryService.getMandiRecommendation(request);
        return ResponseEntity.ok(ApiResponse.success("Mandi recommendations generated successfully", response));
    }

    @PostMapping("/recommend/async")
    @Operation(summary = "Submit asynchronous mandi recommendation job", description = "Submits a recommendation request for background queue processing",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "202",
                    description = "Recommendation job accepted and queued",
                    content = @Content(schema = @Schema(implementation = ModelAppAsyncJobAcceptedResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "422", description = "Validation error"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "503", description = "Queue unavailable")
    })
    public ResponseEntity<ApiResponse<ModelAppAsyncJobAcceptedResponse>> submitAsyncRecommendation(
            @Valid @RequestBody ModelAppRecommendationRequest request) {
        ModelAppAsyncJobAcceptedResponse response = aiAdvisoryService.submitAsyncRecommendation(request);
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .body(ApiResponse.success("Recommendation job accepted and queued", response));
    }

    @GetMapping("/jobs/{jobId}")
    @Operation(summary = "Poll asynchronous AI job status", description = "Retrieves current status and result for an enqueued AI job",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Job status retrieved successfully",
                    content = @Content(schema = @Schema(implementation = ModelAppJobStatusResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "Job not found")
    })
    public ResponseEntity<ApiResponse<ModelAppJobStatusResponse>> getJobStatus(
            @Parameter(description = "Unique UUID of the async job")
            @PathVariable String jobId) {
        ModelAppJobStatusResponse response = aiAdvisoryService.getJobStatus(jobId);
        return ResponseEntity.ok(ApiResponse.success("Job status retrieved successfully", response));
    }

    @PostMapping("/query")
    @Operation(summary = "Natural language farmer advisory & intelligent query routing",
            description = "Classifies farmer questions and routes dynamically to Market Data, ML Price Prediction, Mandi Recommendation, or General LLM Advisory",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Query routed and processed successfully",
                    content = @Content(schema = @Schema(implementation = com.marketlink.backend.ai.dto.query.AiQueryResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "Invalid query or missing parameters"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "422", description = "Validation error"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "502", description = "Upstream AI model or LLM error"),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "503", description = "AI service offline")
    })
    public ResponseEntity<ApiResponse<com.marketlink.backend.ai.dto.query.AiQueryResponse>> processNaturalLanguageQuery(
            @Valid @RequestBody com.marketlink.backend.ai.dto.query.AiNaturalLanguageQueryRequest request) {
        com.marketlink.backend.ai.dto.query.AiQueryResponse response = aiAdvisoryService.routeNaturalLanguageQuery(request);
        return ResponseEntity.ok(ApiResponse.success("Query processed successfully", response));
    }

    @GetMapping("/health")
    @Operation(summary = "Model-app health probe", description = "Checks connectivity and liveness of the underlying Model-app")
    public ResponseEntity<ApiResponse<ModelAppHealthResponse>> checkHealth() {
        ModelAppHealthResponse response = aiAdvisoryService.checkHealth();
        return ResponseEntity.ok(ApiResponse.success("Model-app is healthy", response));
    }

    @GetMapping("/ready")
    @Operation(summary = "Model-app readiness probe", description = "Checks readiness of Redis, RabbitMQ, and ModelPredictor in Model-app")
    public ResponseEntity<ApiResponse<ModelAppReadinessResponse>> checkReadiness() {
        ModelAppReadinessResponse response = aiAdvisoryService.checkReadiness();
        HttpStatus status = Boolean.TRUE.equals(response.getReady()) ? HttpStatus.OK : HttpStatus.SERVICE_UNAVAILABLE;
        return ResponseEntity.status(status).body(ApiResponse.success("Model-app readiness evaluated", response));
    }
}
