package com.marketlink.backend.ai.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.ai.dto.modelapp.*;
import com.marketlink.backend.ai.exception.*;
import com.marketlink.backend.common.context.CorrelationIdContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import java.io.IOException;
import java.net.SocketTimeoutException;
import java.util.concurrent.TimeoutException;

/**
 * Production implementation of ModelAppClient communicating with FastAPI Model-app via RestClient.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class HttpModelAppClient implements ModelAppClient {

    private final RestClient modelAppRestClient;
    private final ObjectMapper objectMapper;

    @Override
    public ModelAppHealthResponse checkHealth() {
        return execute(() -> modelAppRestClient.get()
                .uri("/health")
                .header(CorrelationIdContext.CORRELATION_ID_HEADER, CorrelationIdContext.getCorrelationId())
                .accept(MediaType.APPLICATION_JSON)
                .retrieve()
                .body(ModelAppHealthResponse.class));
    }

    @Override
    public ModelAppReadinessResponse checkReadiness() {
        return execute(() -> modelAppRestClient.get()
                .uri("/ready")
                .header(CorrelationIdContext.CORRELATION_ID_HEADER, CorrelationIdContext.getCorrelationId())
                .accept(MediaType.APPLICATION_JSON)
                .retrieve()
                .body(ModelAppReadinessResponse.class));
    }

    @Override
    public ModelAppPredictionResponse predictPrice(ModelAppPredictionRequest request) {
        log.info("Dispatching price prediction to Model-app for commodity '{}' in market '{}'",
                request.getCommodity(), request.getMarket());
        return execute(() -> modelAppRestClient.post()
                .uri("/api/v1/predict")
                .header(CorrelationIdContext.CORRELATION_ID_HEADER, CorrelationIdContext.getCorrelationId())
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(ModelAppPredictionResponse.class));
    }

    @Override
    public ModelAppRecommendationResponse getRecommendation(ModelAppRecommendationRequest request) {
        log.info("Dispatching synchronous recommendation to Model-app for commodity '{}' at ({}, {})",
                request.getCommodity(), request.getFarmerLatitude(), request.getFarmerLongitude());
        return execute(() -> modelAppRestClient.post()
                .uri("/api/v1/recommend")
                .header(CorrelationIdContext.CORRELATION_ID_HEADER, CorrelationIdContext.getCorrelationId())
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(ModelAppRecommendationResponse.class));
    }

    @Override
    public ModelAppAsyncJobAcceptedResponse submitAsyncRecommendation(ModelAppRecommendationRequest request) {
        log.info("Submitting asynchronous recommendation job to Model-app for commodity '{}'",
                request.getCommodity());
        return execute(() -> modelAppRestClient.post()
                .uri("/api/v1/recommend/async")
                .header(CorrelationIdContext.CORRELATION_ID_HEADER, CorrelationIdContext.getCorrelationId())
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(ModelAppAsyncJobAcceptedResponse.class));
    }

    @Override
    public ModelAppJobStatusResponse getJobStatus(String jobId) {
        log.debug("Polling status for Model-app job '{}'", jobId);
        return execute(() -> modelAppRestClient.get()
                .uri("/api/v1/jobs/{jobId}", jobId)
                .header(CorrelationIdContext.CORRELATION_ID_HEADER, CorrelationIdContext.getCorrelationId())
                .accept(MediaType.APPLICATION_JSON)
                .retrieve()
                .body(ModelAppJobStatusResponse.class));
    }

    @Override
    public ModelAppQueryResponse processGeneralQuery(ModelAppQueryRequest request) {
        log.info("Forwarding farmer query to Model-app LLM advisory");
        return execute(() -> modelAppRestClient.post()
                .uri("/api/v1/query")
                .header(CorrelationIdContext.CORRELATION_ID_HEADER, CorrelationIdContext.getCorrelationId())
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(ModelAppQueryResponse.class));
    }

    @Override
    public ModelAppMarketDataResponse getMarketData(String commodity, java.util.List<String> markets, String state, Integer limit) {
        log.info("Querying market data from Model-app for commodity '{}', state '{}'", commodity, state);
        return execute(() -> modelAppRestClient.get()
                .uri(uriBuilder -> {
                    uriBuilder.path("/api/v1/market-data");
                    if (commodity != null && !commodity.isBlank()) {
                        uriBuilder.queryParam("commodity", commodity);
                    }
                    if (state != null && !state.isBlank()) {
                        uriBuilder.queryParam("state", state);
                    }
                    if (markets != null && !markets.isEmpty()) {
                        for (String m : markets) {
                            uriBuilder.queryParam("markets", m);
                        }
                    }
                    if (limit != null && limit > 0) {
                        uriBuilder.queryParam("limit", limit);
                    }
                    return uriBuilder.build();
                })
                .header(CorrelationIdContext.CORRELATION_ID_HEADER, CorrelationIdContext.getCorrelationId())
                .accept(MediaType.APPLICATION_JSON)
                .retrieve()
                .body(ModelAppMarketDataResponse.class));
    }

    /**
     * Executes HTTP operation with resilient exception translation.
     */
    private <T> T execute(HttpCallable<T> callable) {
        try {
            return callable.call();
        } catch (RestClientResponseException ex) {
            throw translateHttpException(ex);
        } catch (ResourceAccessException ex) {
            throw translateResourceAccessException(ex);
        } catch (ModelAppException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("Unexpected error communicating with Model-app: {}", ex.getMessage(), ex);
            throw new ModelAppException("Unexpected communication failure with AI service",
                    org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR, ex);
        }
    }

    private ModelAppException translateHttpException(RestClientResponseException ex) {
        HttpStatusCode status = ex.getStatusCode();
        String rawBody = ex.getResponseBodyAsString();
        String errorMessage = extractErrorMessage(rawBody, status);

        log.warn("Model-app responded with error HTTP {}: {}", status.value(), errorMessage);

        if (status.value() == 404) {
            return new ModelAppNotFoundException(errorMessage, ex);
        } else if (status.value() == 422 || status.value() == 400) {
            return new ModelAppValidationException(errorMessage, ex);
        } else if (status.value() == 502) {
            return new ModelAppBadGatewayException(errorMessage, ex);
        } else if (status.value() == 503) {
            return new ModelAppUnavailableException(errorMessage, ex);
        } else if (status.value() == 504) {
            return new ModelAppTimeoutException(errorMessage, ex);
        } else {
            return new ModelAppException(errorMessage, org.springframework.http.HttpStatus.valueOf(status.value()), ex);
        }
    }

    private ModelAppException translateResourceAccessException(ResourceAccessException ex) {
        Throwable cause = ex.getCause();
        if (cause instanceof SocketTimeoutException || cause instanceof TimeoutException
                || (ex.getMessage() != null && ex.getMessage().toLowerCase().contains("timed out"))) {
            log.error("Model-app request timed out: {}", ex.getMessage());
            return new ModelAppTimeoutException("Model-app operation timed out", ex);
        }
        log.error("Model-app connection refused or unreachable: {}", ex.getMessage());
        return new ModelAppUnavailableException("Model-app connection refused or unavailable", ex);
    }

    private String extractErrorMessage(String responseBody, HttpStatusCode status) {
        if (responseBody == null || responseBody.isBlank()) {
            return "Model-app returned HTTP " + status.value();
        }
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            if (root.has("error")) {
                JsonNode errorNode = root.get("error");
                if (errorNode.has("message") && !errorNode.get("message").asText().isBlank()) {
                    return errorNode.get("message").asText();
                }
                if (errorNode.has("code")) {
                    return errorNode.get("code").asText();
                }
            }
            if (root.has("detail")) {
                JsonNode detailNode = root.get("detail");
                if (detailNode.isTextual()) {
                    return detailNode.asText();
                }
                return detailNode.toString();
            }
            if (root.has("message")) {
                return root.get("message").asText();
            }
        } catch (IOException e) {
            log.debug("Could not parse Model-app error JSON: {}", e.getMessage());
        }
        return "Model-app returned HTTP " + status.value() + ": " + responseBody;
    }

    @FunctionalInterface
    private interface HttpCallable<T> {
        T call() throws Exception;
    }
}
