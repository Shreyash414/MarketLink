package com.marketlink.backend.ai.classifier;

import com.marketlink.backend.ai.dto.query.AiNaturalLanguageQueryRequest;
import com.marketlink.backend.ai.enums.AiQueryIntent;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class AiQueryClassifierTest {

    private AiQueryClassifier classifier;

    @BeforeEach
    void setUp() {
        classifier = new AiQueryClassifier();
    }

    @Test
    @DisplayName("Classifies spot market price inquiry as MARKET_DATA")
    void testMarketDataClassification() {
        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("What is today's onion price in Nagpur?")
                .build();

        AiQueryClassifier.ClassificationResult result = classifier.classify(req);

        assertEquals(AiQueryIntent.MARKET_DATA, result.getIntent());
        assertEquals("Onion", result.getExtractedCommodity());
        assertEquals("Nagpur", result.getExtractedMarket());
        assertTrue(result.getConfidence() >= 0.85);
    }

    @Test
    @DisplayName("Classifies future price forecast as PRICE_PREDICTION")
    void testPricePredictionClassification() {
        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("What price can I expect for onions next week?")
                .build();

        AiQueryClassifier.ClassificationResult result = classifier.classify(req);

        assertEquals(AiQueryIntent.PRICE_PREDICTION, result.getIntent());
        assertEquals("Onion", result.getExtractedCommodity());
        assertTrue(result.getConfidence() >= 0.85);
    }

    @Test
    @DisplayName("Classifies selling decision query as MANDI_RECOMMENDATION")
    void testMandiRecommendationClassification() {
        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("Which mandi should I sell my onions in?")
                .build();

        AiQueryClassifier.ClassificationResult result = classifier.classify(req);

        assertEquals(AiQueryIntent.MANDI_RECOMMENDATION, result.getIntent());
        assertEquals("Onion", result.getExtractedCommodity());
        assertTrue(result.getConfidence() >= 0.85);
    }

    @Test
    @DisplayName("Classifies agronomy and storage questions as GENERAL_ADVISORY")
    void testGeneralAdvisoryClassification() {
        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("What is the best way to store onions to prevent rot and fungus?")
                .build();

        AiQueryClassifier.ClassificationResult result = classifier.classify(req);

        assertEquals(AiQueryIntent.GENERAL_ADVISORY, result.getIntent());
        assertEquals("Onion", result.getExtractedCommodity());
        assertTrue(result.getConfidence() >= 0.80);
    }

    @Test
    @DisplayName("Classifies dual prediction + recommendation question as COMBINED_ANALYSIS")
    void testCombinedAnalysisClassification() {
        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("Which mandi should I sell my onions in next week considering expected prices?")
                .build();

        AiQueryClassifier.ClassificationResult result = classifier.classify(req);

        assertEquals(AiQueryIntent.COMBINED_ANALYSIS, result.getIntent());
        assertEquals("Onion", result.getExtractedCommodity());
        assertTrue(result.getConfidence() >= 0.90);
    }

    @Test
    @DisplayName("Recognizes conversational Hinglish price forecast as PRICE_PREDICTION")
    void testHinglishPricePrediction() {
        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("bhai next week onion ka kya bhav milega?")
                .build();

        AiQueryClassifier.ClassificationResult result = classifier.classify(req);

        assertEquals(AiQueryIntent.PRICE_PREDICTION, result.getIntent());
        assertEquals("Onion", result.getExtractedCommodity());
        assertTrue(result.getConfidence() >= 0.85);
    }

    @Test
    @DisplayName("Recognizes conversational Hinglish market price query as MARKET_DATA")
    void testHinglishMarketData() {
        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("aaj ka aloo ka rate kya hai Bareilly mandi me?")
                .build();

        AiQueryClassifier.ClassificationResult result = classifier.classify(req);

        assertEquals(AiQueryIntent.MARKET_DATA, result.getIntent());
        assertEquals("Potato", result.getExtractedCommodity());
        assertEquals("Bareilly", result.getExtractedMarket());
    }

    @Test
    @DisplayName("Recognizes Hinglish recommendation phrasing 'kahan bechun' as MANDI_RECOMMENDATION")
    void testHinglishMandiRecommendation() {
        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("kahan bechun pyaj achha rate paane ke liye?")
                .build();

        AiQueryClassifier.ClassificationResult result = classifier.classify(req);

        assertEquals(AiQueryIntent.MANDI_RECOMMENDATION, result.getIntent());
        assertEquals("Onion", result.getExtractedCommodity());
    }

    @Test
    @DisplayName("Falls back to GENERAL_ADVISORY on ambiguous general questions")
    void testAmbiguousFallback() {
        AiNaturalLanguageQueryRequest req = AiNaturalLanguageQueryRequest.builder()
                .query("Good morning, what should I know about agriculture today?")
                .build();

        AiQueryClassifier.ClassificationResult result = classifier.classify(req);

        assertEquals(AiQueryIntent.GENERAL_ADVISORY, result.getIntent());
    }
}
