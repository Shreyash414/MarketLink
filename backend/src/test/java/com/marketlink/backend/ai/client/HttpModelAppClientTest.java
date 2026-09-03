package com.marketlink.backend.ai.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.ai.config.ModelAppProperties;
import com.marketlink.backend.ai.dto.modelapp.*;
import com.marketlink.backend.ai.exception.*;
import com.marketlink.backend.common.context.CorrelationIdContext;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

class HttpModelAppClientTest {

    private static final String BASE_URL = "http://localhost:8000";

    private MockRestServiceServer mockServer;
    private HttpModelAppClient client;
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();

        ModelAppProperties properties = new ModelAppProperties();
        properties.setBaseUrl(BASE_URL);
        properties.setConnectTimeoutMs(1000);
        properties.setReadTimeoutMs(1000);

        RestClient.Builder restClientBuilder = RestClient.builder().baseUrl(BASE_URL);
        mockServer = MockRestServiceServer.bindTo(restClientBuilder).build();
        RestClient restClient = restClientBuilder.build();

        client = new HttpModelAppClient(restClient, objectMapper);
        CorrelationIdContext.clear();
    }

    @Test
    @DisplayName("1. Successful price prediction returns parsed response")
    void test01_successfulPrediction() {
        String json = """
                {
                    "market": "Bareilly",
                    "commodity": "Onion",
                    "current_price": 1850.0,
                    "predicted_price": 1920.0,
                    "expected_change": 70.0,
                    "expected_change_pct": 3.78,
                    "expected_direction": "UP",
                    "usage_status": "PRODUCTION_READY",
                    "reliability_score": 92.0,
                    "quality_class": "STRONG",
                    "data_source": "DIRECT"
                }
                """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/predict"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andRespond(withSuccess(json, MediaType.APPLICATION_JSON));

        ModelAppPredictionRequest req = ModelAppPredictionRequest.builder()
                .market("Bareilly")
                .commodity("Onion")
                .currentPrice(1850.0)
                .build();

        ModelAppPredictionResponse resp = client.predictPrice(req);
        assertNotNull(resp);
        assertEquals("Bareilly", resp.getMarket());
        assertEquals(1920.0, resp.getPredictedPrice());
        assertEquals("UP", resp.getExpectedDirection());
        mockServer.verify();
    }

    @Test
    @DisplayName("2. Successful recommendation returns list of mandis and net returns")
    void test02_successfulRecommendation() {
        String json = """
                {
                    "commodity": "Onion",
                    "farmer_latitude": 28.6139,
                    "farmer_longitude": 77.2090,
                    "quantity_quintals": 10.0,
                    "recommended_mandi": "Bareilly",
                    "total_mandis_evaluated": 1,
                    "overall_data_source": "CACHE",
                    "recommendations": [
                        {
                            "rank": 1,
                            "mandi": "Bareilly",
                            "state": "Uttar Pradesh",
                            "district": "Bareilly",
                            "distance_km": 15.2,
                            "current_price": 1850.0,
                            "predicted_price": 1920.0,
                            "expected_change": 70.0,
                            "expected_change_pct": 3.78,
                            "expected_direction": "UP",
                            "transport_cost": 45.0,
                            "market_fee": 18.0,
                            "gross_revenue": 19200.0,
                            "total_cost": 630.0,
                            "net_return": 18570.0,
                            "net_price_per_quintal": 1857.0,
                            "risk_level": "LOW",
                            "confidence_score": 85.0,
                            "recommendation_label": "RECOMMENDED",
                            "model_usage_status": "PRODUCTION_READY",
                            "model_reliability_score": 90.0,
                            "model_quality_class": "STRONG",
                            "data_source": "CACHE"
                        }
                    ]
                }
                """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/recommend"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(json, MediaType.APPLICATION_JSON));

        ModelAppRecommendationRequest req = ModelAppRecommendationRequest.builder()
                .farmerLatitude(28.6139)
                .farmerLongitude(77.2090)
                .quantityQuintals(10.0)
                .commodity("Onion")
                .build();

        ModelAppRecommendationResponse resp = client.getRecommendation(req);
        assertNotNull(resp);
        assertEquals("Bareilly", resp.getRecommendedMandi());
        assertEquals(1, resp.getRecommendations().size());
        assertEquals(18570.0, resp.getRecommendations().get(0).getNetReturn());
        mockServer.verify();
    }

    @Test
    @DisplayName("3. Successful general query returns LLM trade intent")
    void test03_successfulGeneralQuery() {
        String json = """
                {
                    "query": "Should I sell onions in Bareilly today?",
                    "intent": "PRICE_QUERY",
                    "entities": {"commodity": "Onion", "market": "Bareilly"},
                    "response": "Prices in Bareilly are trending upward by 3.8%.",
                    "language": "en",
                    "confidence": 0.95,
                    "source": "OLLAMA_LLM",
                    "model": "llama3",
                    "timestamp": "2026-09-03T12:00:00Z"
                }
                """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/query"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(json, MediaType.APPLICATION_JSON));

        ModelAppQueryRequest req = ModelAppQueryRequest.builder()
                .query("Should I sell onions in Bareilly today?")
                .language("en")
                .build();

        ModelAppQueryResponse resp = client.processGeneralQuery(req);
        assertNotNull(resp);
        assertEquals("PRICE_QUERY", resp.getIntent());
        assertTrue(resp.getResponse().contains("trending upward"));
        mockServer.verify();
    }

    @Test
    @DisplayName("4. Async job submission returns HTTP 202 with job ID")
    void test04_asyncJobSubmission() {
        String json = """
                {
                    "job_id": "job-uuid-12345",
                    "status": "QUEUED",
                    "operation": "RECOMMEND_MANDI",
                    "created_at": "2026-09-03T12:00:00Z",
                    "message": "Job successfully enqueued",
                    "poll_url": "/api/v1/jobs/job-uuid-12345"
                }
                """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/recommend/async"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withStatus(HttpStatus.ACCEPTED).body(json).contentType(MediaType.APPLICATION_JSON));

        ModelAppRecommendationRequest req = ModelAppRecommendationRequest.builder()
                .farmerLatitude(28.6139)
                .farmerLongitude(77.2090)
                .quantityQuintals(10.0)
                .build();

        ModelAppAsyncJobAcceptedResponse resp = client.submitAsyncRecommendation(req);
        assertNotNull(resp);
        assertEquals("job-uuid-12345", resp.getJobId());
        assertEquals("QUEUED", resp.getStatus());
        mockServer.verify();
    }

    @Test
    @DisplayName("5. Job status retrieval returns current processing state")
    void test05_jobStatusRetrieval() {
        String json = """
                {
                    "job_id": "job-uuid-12345",
                    "operation": "RECOMMEND_MANDI",
                    "status": "COMPLETED",
                    "created_at": "2026-09-03T12:00:00Z",
                    "updated_at": "2026-09-03T12:00:02Z",
                    "completed_at": "2026-09-03T12:00:02Z",
                    "result": {"recommended_mandi": "Bareilly", "net_return": 18570.0}
                }
                """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/jobs/job-uuid-12345"))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess(json, MediaType.APPLICATION_JSON));

        ModelAppJobStatusResponse resp = client.getJobStatus("job-uuid-12345");
        assertNotNull(resp);
        assertEquals("COMPLETED", resp.getStatus());
        assertNotNull(resp.getResult());
        assertEquals("Bareilly", resp.getResult().get("recommended_mandi"));
        mockServer.verify();
    }

    @Test
    @DisplayName("6. Model-app HTTP 400 Bad Request throws ModelAppValidationException")
    void test06_modelApp400BadRequest() {
        String errorJson = """
                {"error": {"code": "INVALID_INPUT", "message": "Price must be positive"}}
                """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/predict"))
                .andRespond(withBadRequest().body(errorJson).contentType(MediaType.APPLICATION_JSON));

        ModelAppPredictionRequest req = ModelAppPredictionRequest.builder()
                .market("Bareilly")
                .currentPrice(-100.0)
                .build();

        ModelAppValidationException ex = assertThrows(
                ModelAppValidationException.class,
                () -> client.predictPrice(req)
        );
        assertTrue(ex.getMessage().contains("Price must be positive"));
        mockServer.verify();
    }

    @Test
    @DisplayName("7. Model-app HTTP 404 Not Found throws ModelAppNotFoundException")
    void test07_modelApp404NotFound() {
        String errorJson = """
                {"error": {"code": "JOB_NOT_FOUND", "message": "Job unknown-job-id not found"}}
                """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/jobs/unknown-job-id"))
                .andRespond(withRawStatus(404).body(errorJson).contentType(MediaType.APPLICATION_JSON));

        ModelAppNotFoundException ex = assertThrows(
                ModelAppNotFoundException.class,
                () -> client.getJobStatus("unknown-job-id")
        );
        assertTrue(ex.getMessage().contains("not found"));
        mockServer.verify();
    }

    @Test
    @DisplayName("8. Model-app HTTP 422 Validation Error throws ModelAppValidationException")
    void test08_modelApp422ValidationError() {
        String errorJson = """
                {"error": {"code": "VALIDATION_ERROR", "message": "Latitude must be between -90 and 90"}}
                """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/recommend"))
                .andRespond(withRawStatus(422).body(errorJson).contentType(MediaType.APPLICATION_JSON));

        ModelAppRecommendationRequest req = ModelAppRecommendationRequest.builder()
                .farmerLatitude(120.0)
                .farmerLongitude(77.0)
                .quantityQuintals(10.0)
                .build();

        ModelAppValidationException ex = assertThrows(
                ModelAppValidationException.class,
                () -> client.getRecommendation(req)
        );
        assertTrue(ex.getMessage().contains("Latitude must be between"));
        mockServer.verify();
    }

    @Test
    @DisplayName("9. Model-app HTTP 500 Internal Server Error throws ModelAppException")
    void test09_modelApp500ServerError() {
        String errorJson = """
                {"error": {"code": "INTERNAL_SERVER_ERROR", "message": "Unexpected computation error"}}
                """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/predict"))
                .andRespond(withServerError().body(errorJson).contentType(MediaType.APPLICATION_JSON));

        ModelAppPredictionRequest req = ModelAppPredictionRequest.builder()
                .market("Bareilly")
                .currentPrice(1850.0)
                .build();

        ModelAppException ex = assertThrows(
                ModelAppException.class,
                () -> client.predictPrice(req)
        );
        assertTrue(ex.getMessage().contains("Unexpected computation error"));
        mockServer.verify();
    }

    @Test
    @DisplayName("10. Model-app HTTP 502 Bad Gateway throws ModelAppBadGatewayException")
    void test10_modelApp502BadGateway() {
        String errorJson = """
                {"error": {"code": "OLLAMA_SERVICE_ERROR", "message": "Upstream Ollama returned empty generation"}}
                """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/query"))
                .andRespond(withRawStatus(502).body(errorJson).contentType(MediaType.APPLICATION_JSON));

        ModelAppQueryRequest req = ModelAppQueryRequest.builder().query("Test").build();

        ModelAppBadGatewayException ex = assertThrows(
                ModelAppBadGatewayException.class,
                () -> client.processGeneralQuery(req)
        );
        assertTrue(ex.getMessage().contains("Upstream Ollama"));
        mockServer.verify();
    }

    @Test
    @DisplayName("11. Model-app HTTP 503 Service Unavailable throws ModelAppUnavailableException")
    void test11_modelApp503ServiceUnavailable() {
        String errorJson = """
                {"error": {"code": "MESSAGING_ERROR", "message": "RabbitMQ broker connection refused"}}
                """;

        mockServer.expect(requestTo(BASE_URL + "/api/v1/recommend/async"))
                .andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE).body(errorJson).contentType(MediaType.APPLICATION_JSON));

        ModelAppRecommendationRequest req = ModelAppRecommendationRequest.builder()
                .farmerLatitude(28.0)
                .farmerLongitude(77.0)
                .quantityQuintals(10.0)
                .build();

        ModelAppUnavailableException ex = assertThrows(
                ModelAppUnavailableException.class,
                () -> client.submitAsyncRecommendation(req)
        );
        assertTrue(ex.getMessage().contains("connection refused"));
        mockServer.verify();
    }

    @Test
    @DisplayName("12. Correlation ID header is propagated to Model-app")
    void test12_correlationIdPropagation() {
        CorrelationIdContext.setCorrelationId("test-trace-uuid-999");

        mockServer.expect(requestTo(BASE_URL + "/health"))
                .andExpect(header("X-Correlation-ID", "test-trace-uuid-999"))
                .andRespond(withSuccess("{\"status\": \"HEALTHY\"}", MediaType.APPLICATION_JSON));

        ModelAppHealthResponse resp = client.checkHealth();
        assertEquals("HEALTHY", resp.getStatus());
        mockServer.verify();
    }

    @Test
    @DisplayName("13. Health endpoint maps cleanly")
    void test13_healthProbe() {
        String healthJson = "{\"status\": \"HEALTHY\", \"service\": \"marketlink-ai\", \"version\": \"1.0.0\"}";
        mockServer.expect(requestTo(BASE_URL + "/health"))
                .andRespond(withSuccess(healthJson, MediaType.APPLICATION_JSON));

        ModelAppHealthResponse health = client.checkHealth();
        assertEquals("HEALTHY", health.getStatus());
        mockServer.verify();
    }

    @Test
    @DisplayName("14. Readiness endpoint maps cleanly")
    void test14_readinessProbe() {
        String readyJson = "{\"ready\": true, \"status\": \"READY\", \"dependencies\": {\"redis\": {\"status\": \"UP\"}}}";
        mockServer.expect(requestTo(BASE_URL + "/ready"))
                .andRespond(withSuccess(readyJson, MediaType.APPLICATION_JSON));

        ModelAppReadinessResponse ready = client.checkReadiness();
        assertTrue(ready.getReady());
        assertEquals("READY", ready.getStatus());
        mockServer.verify();
    }

    @Test
    @DisplayName("15. Connection failure throws ModelAppUnavailableException")
    void test15_connectionFailure() {
        mockServer.expect(requestTo(BASE_URL + "/health"))
                .andRespond((request) -> {
                    throw new org.springframework.web.client.ResourceAccessException("Connection refused");
                });

        assertThrows(ModelAppUnavailableException.class, () -> client.checkHealth());
        mockServer.verify();
    }

    @Test
    @DisplayName("16. Timeout throws ModelAppTimeoutException")
    void test16_timeout() {
        mockServer.expect(requestTo(BASE_URL + "/health"))
                .andRespond((request) -> {
                    throw new org.springframework.web.client.ResourceAccessException("Read timed out");
                });

        assertThrows(ModelAppTimeoutException.class, () -> client.checkHealth());
        mockServer.verify();
    }

    @Test
    @DisplayName("17. Market data query maps response cleanly")
    void test17_marketDataRetrieval() {
        String json = """
                {
                    "commodity": "Onion",
                    "data_source": "LIVE",
                    "is_live": true,
                    "record_count": 1,
                    "records": [
                        {
                            "state": "Maharashtra",
                            "district": "Nagpur",
                            "market": "Nagpur",
                            "commodity": "Onion",
                            "modal_price": 1950.0,
                            "min_price": 1800.0,
                            "max_price": 2100.0,
                            "date": "2026-09-03"
                        }
                    ]
                }
                """;

        mockServer.expect(requestTo(org.hamcrest.Matchers.startsWith(BASE_URL + "/api/v1/market-data")))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess(json, MediaType.APPLICATION_JSON));

        ModelAppMarketDataResponse resp = client.getMarketData("Onion", List.of("Nagpur"), null, 20);
        assertNotNull(resp);
        assertEquals("Onion", resp.getCommodity());
        assertEquals(1, resp.getRecordCount());
        assertEquals(1950.0, resp.getRecords().get(0).getModalPrice());
        mockServer.verify();
    }
}
