package com.marketlink.backend.ai.router;

import com.marketlink.backend.ai.classifier.AiQueryClassifier;
import com.marketlink.backend.ai.client.ModelAppClient;
import com.marketlink.backend.ai.dto.modelapp.*;
import com.marketlink.backend.ai.dto.query.AiNaturalLanguageQueryRequest;
import com.marketlink.backend.ai.dto.query.AiQueryResponse;
import com.marketlink.backend.ai.enums.AiQueryIntent;
import com.marketlink.backend.ai.exception.ModelAppValidationException;
import com.marketlink.backend.domain.common.entity.Location;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AiQueryRouterTest {

    @Mock
    private ModelAppClient modelAppClient;

    private AiQueryClassifier classifier;
    private AiQueryRouter router;

    @BeforeEach
    void setUp() {
        classifier = new AiQueryClassifier();
        router = new AiQueryRouter(classifier, modelAppClient);
    }

    @Test
    @DisplayName("GENERAL_ADVISORY invokes processGeneralQuery and NOT ML endpoints")
    void testGeneralAdvisoryRouting() {
        ModelAppQueryResponse mockResponse = ModelAppQueryResponse.builder()
                .query("How to store onions")
                .intent("GENERAL_ADVISORY")
                .response("Store onions in a cool, well-ventilated space.")
                .build();

        when(modelAppClient.processGeneralQuery(any())).thenReturn(mockResponse);

        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("What is the best way to store onions to prevent rot?")
                .build();

        AiQueryResponse response = router.route(req);

        assertNotNull(response);
        assertEquals(AiQueryIntent.GENERAL_ADVISORY, response.getIntent());
        assertTrue(response.getAnswer().contains("cool, well-ventilated"));

        verify(modelAppClient, times(1)).processGeneralQuery(any());
        verify(modelAppClient, never()).predictPrice(any());
        verify(modelAppClient, never()).getRecommendation(any());
        verify(modelAppClient, never()).getMarketData(any(), any(), any(), any());
    }

    @Test
    @DisplayName("MARKET_DATA invokes getMarketData and NOT Ollama")
    void testMarketDataRouting() {
        ModelAppMarketDataResponse mockData = ModelAppMarketDataResponse.builder()
                .commodity("Onion")
                .dataSource("LIVE")
                .isLive(true)
                .recordCount(1)
                .records(List.of(
                        ModelAppMandiPriceRecord.builder()
                                .commodity("Onion")
                                .market("Nagpur")
                                .state("Maharashtra")
                                .modalPrice(1950.0)
                                .date("2026-09-03")
                                .build()
                ))
                .build();

        when(modelAppClient.getMarketData(eq("Onion"), any(), any(), any())).thenReturn(mockData);

        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("What is today's onion price in Nagpur?")
                .build();

        AiQueryResponse response = router.route(req);

        assertNotNull(response);
        assertEquals(AiQueryIntent.MARKET_DATA, response.getIntent());
        assertTrue(response.getAnswer().contains("₹1950.0"));

        verify(modelAppClient, times(1)).getMarketData(eq("Onion"), any(), any(), any());
        verify(modelAppClient, never()).processGeneralQuery(any());
        verify(modelAppClient, never()).predictPrice(any());
    }

    @Test
    @DisplayName("PRICE_PREDICTION invokes predictPrice and NOT Ollama")
    void testPricePredictionRouting() {
        ModelAppPredictionResponse mockPred = ModelAppPredictionResponse.builder()
                .commodity("Onion")
                .market("Bareilly")
                .currentPrice(1850.0)
                .predictedPrice(1920.0)
                .expectedChange(70.0)
                .expectedDirection("UP")
                .qualityClass("STRONG")
                .reliabilityScore(92.0)
                .build();

        when(modelAppClient.predictPrice(any())).thenReturn(mockPred);

        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("What price can I expect for onions next week?")
                .market("Bareilly")
                .build();

        AiQueryResponse response = router.route(req);

        assertNotNull(response);
        assertEquals(AiQueryIntent.PRICE_PREDICTION, response.getIntent());
        assertTrue(response.getAnswer().contains("1920.0"));

        verify(modelAppClient, times(1)).predictPrice(any());
        verify(modelAppClient, never()).processGeneralQuery(any());
        verify(modelAppClient, never()).getRecommendation(any());
    }

    @Test
    @DisplayName("MANDI_RECOMMENDATION invokes getRecommendation with Location and NOT Ollama")
    void testMandiRecommendationRouting() {
        ModelAppRecommendationResponse mockRec = ModelAppRecommendationResponse.builder()
                .commodity("Onion")
                .recommendedMandi("Bareilly")
                .recommendations(List.of(
                        ModelAppMandiItem.builder()
                                .mandi("Bareilly")
                                .state("Uttar Pradesh")
                                .distanceKm(15.2)
                                .netReturn(18570.0)
                                .build()
                ))
                .build();

        when(modelAppClient.getRecommendation(any())).thenReturn(mockRec);

        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("Which mandi should I sell my onions in?")
                .location(Location.of(28.6139, 77.2090))
                .quantityQuintals(10.0)
                .build();

        AiQueryResponse response = router.route(req);

        assertNotNull(response);
        assertEquals(AiQueryIntent.MANDI_RECOMMENDATION, response.getIntent());
        assertTrue(response.getAnswer().contains("Bareilly"));

        verify(modelAppClient, times(1)).getRecommendation(any());
        verify(modelAppClient, never()).processGeneralQuery(any());
        verify(modelAppClient, never()).predictPrice(any());
    }

    @Test
    @DisplayName("MANDI_RECOMMENDATION without coordinates throws ModelAppValidationException")
    void testMandiRecommendationMissingLocationThrows() {
        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("Which mandi should I sell my onions in?")
                .build();

        assertThrows(ModelAppValidationException.class, () -> router.route(req));
        verifyNoInteractions(modelAppClient);
    }

    @Test
    @DisplayName("COMBINED_ANALYSIS invokes BOTH predictPrice and getRecommendation")
    void testCombinedAnalysisRouting() {
        ModelAppPredictionResponse mockPred = ModelAppPredictionResponse.builder()
                .commodity("Onion")
                .market("Bareilly")
                .predictedPrice(1920.0)
                .expectedDirection("UP")
                .build();

        ModelAppRecommendationResponse mockRec = ModelAppRecommendationResponse.builder()
                .commodity("Onion")
                .recommendedMandi("Bareilly")
                .recommendations(List.of(
                        ModelAppMandiItem.builder()
                                .mandi("Bareilly")
                                .netReturn(18570.0)
                                .build()
                ))
                .build();

        when(modelAppClient.predictPrice(any())).thenReturn(mockPred);
        when(modelAppClient.getRecommendation(any())).thenReturn(mockRec);

        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("Which mandi should I sell my onions in next week considering expected price?")
                .location(Location.of(28.6139, 77.2090))
                .quantityQuintals(10.0)
                .build();

        AiQueryResponse response = router.route(req);

        assertNotNull(response);
        assertEquals(AiQueryIntent.COMBINED_ANALYSIS, response.getIntent());
        assertNotNull(response.getPrediction());
        assertNotNull(response.getRecommendation());
        assertNotNull(response.getExplanation());

        verify(modelAppClient, times(1)).predictPrice(any());
        verify(modelAppClient, times(1)).getRecommendation(any());
        verify(modelAppClient, never()).processGeneralQuery(any());
    }
}
