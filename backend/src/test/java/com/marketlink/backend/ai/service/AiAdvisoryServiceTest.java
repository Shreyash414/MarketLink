package com.marketlink.backend.ai.service;

import com.marketlink.backend.ai.client.ModelAppClient;
import com.marketlink.backend.ai.dto.modelapp.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AiAdvisoryServiceTest {

    @Mock
    private ModelAppClient modelAppClient;

    @Mock
    private com.marketlink.backend.ai.router.AiQueryRouter aiQueryRouter;

    @InjectMocks
    private AiAdvisoryService aiAdvisoryService;

    @Test
    @DisplayName("Service delegates natural language routing to AiQueryRouter")
    void testRouteNaturalLanguageQueryDelegation() {
        com.marketlink.backend.ai.dto.query.AiNaturalLanguageQueryRequest req =
                com.marketlink.backend.ai.dto.query.AiNaturalLanguageQueryRequest.builder()
                        .query("What price can I expect for onions next week?")
                        .build();

        com.marketlink.backend.ai.dto.query.AiQueryResponse expected =
                com.marketlink.backend.ai.dto.query.AiQueryResponse.builder()
                        .intent(com.marketlink.backend.ai.enums.AiQueryIntent.PRICE_PREDICTION)
                        .answer("Predicted price is 1920.0")
                        .build();

        when(aiQueryRouter.route(req)).thenReturn(expected);

        com.marketlink.backend.ai.dto.query.AiQueryResponse actual = aiAdvisoryService.routeNaturalLanguageQuery(req);
        assertSame(expected, actual);
        verify(aiQueryRouter, times(1)).route(req);
    }

    @Test
    @DisplayName("Service delegates price prediction to ModelAppClient")
    void testPredictPriceDelegation() {
        ModelAppPredictionRequest req = ModelAppPredictionRequest.builder()
                .market("Bareilly")
                .commodity("Onion")
                .currentPrice(1850.0)
                .build();

        ModelAppPredictionResponse expected = ModelAppPredictionResponse.builder()
                .market("Bareilly")
                .commodity("Onion")
                .predictedPrice(1920.0)
                .build();

        when(modelAppClient.predictPrice(req)).thenReturn(expected);

        ModelAppPredictionResponse actual = aiAdvisoryService.predictPrice(req);
        assertSame(expected, actual);
        verify(modelAppClient, times(1)).predictPrice(req);
    }

    @Test
    @DisplayName("Service delegates synchronous recommendation to ModelAppClient")
    void testGetRecommendationDelegation() {
        ModelAppRecommendationRequest req = ModelAppRecommendationRequest.builder()
                .farmerLatitude(28.6139)
                .farmerLongitude(77.2090)
                .quantityQuintals(10.0)
                .commodity("Onion")
                .build();

        ModelAppRecommendationResponse expected = ModelAppRecommendationResponse.builder()
                .commodity("Onion")
                .recommendedMandi("Bareilly")
                .recommendations(List.of())
                .build();

        when(modelAppClient.getRecommendation(req)).thenReturn(expected);

        ModelAppRecommendationResponse actual = aiAdvisoryService.getMandiRecommendation(req);
        assertSame(expected, actual);
        verify(modelAppClient, times(1)).getRecommendation(req);
    }

    @Test
    @DisplayName("Service delegates async recommendation to ModelAppClient")
    void testSubmitAsyncRecommendationDelegation() {
        ModelAppRecommendationRequest req = ModelAppRecommendationRequest.builder()
                .farmerLatitude(28.6139)
                .farmerLongitude(77.2090)
                .quantityQuintals(10.0)
                .build();

        ModelAppAsyncJobAcceptedResponse expected = ModelAppAsyncJobAcceptedResponse.builder()
                .jobId("test-uuid")
                .status("QUEUED")
                .build();

        when(modelAppClient.submitAsyncRecommendation(req)).thenReturn(expected);

        ModelAppAsyncJobAcceptedResponse actual = aiAdvisoryService.submitAsyncRecommendation(req);
        assertSame(expected, actual);
        verify(modelAppClient, times(1)).submitAsyncRecommendation(req);
    }

    @Test
    @DisplayName("Service delegates job status polling to ModelAppClient")
    void testGetJobStatusDelegation() {
        ModelAppJobStatusResponse expected = ModelAppJobStatusResponse.builder()
                .jobId("test-uuid")
                .status("COMPLETED")
                .build();

        when(modelAppClient.getJobStatus("test-uuid")).thenReturn(expected);

        ModelAppJobStatusResponse actual = aiAdvisoryService.getJobStatus("test-uuid");
        assertSame(expected, actual);
        verify(modelAppClient, times(1)).getJobStatus("test-uuid");
    }

    @Test
    @DisplayName("Service delegates general query to ModelAppClient")
    void testProcessGeneralQueryDelegation() {
        ModelAppQueryRequest req = ModelAppQueryRequest.builder()
                .query("Market trends")
                .language("en")
                .build();

        ModelAppQueryResponse expected = ModelAppQueryResponse.builder()
                .intent("PRICE_QUERY")
                .response("Prices are rising")
                .build();

        when(modelAppClient.processGeneralQuery(req)).thenReturn(expected);

        ModelAppQueryResponse actual = aiAdvisoryService.processGeneralQuery(req);
        assertSame(expected, actual);
        verify(modelAppClient, times(1)).processGeneralQuery(req);
    }

    @Test
    @DisplayName("Service delegates health and readiness to ModelAppClient")
    void testHealthAndReadinessDelegation() {
        ModelAppHealthResponse healthExpected = ModelAppHealthResponse.builder().status("HEALTHY").build();
        when(modelAppClient.checkHealth()).thenReturn(healthExpected);

        ModelAppReadinessResponse readyExpected = ModelAppReadinessResponse.builder().ready(true).build();
        when(modelAppClient.checkReadiness()).thenReturn(readyExpected);

        assertSame(healthExpected, aiAdvisoryService.checkHealth());
        assertSame(readyExpected, aiAdvisoryService.checkReadiness());
    }
}
