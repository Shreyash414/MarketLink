package com.marketlink.backend.ai.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.ai.dto.modelapp.*;
import com.marketlink.backend.ai.exception.*;
import com.marketlink.backend.ai.service.AiAdvisoryService;
import com.marketlink.backend.common.exception.GlobalExceptionHandler;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@ExtendWith(MockitoExtension.class)
class AiAdvisoryControllerTest {

    private MockMvc mockMvc;
    private ObjectMapper objectMapper;

    @Mock
    private AiAdvisoryService aiAdvisoryService;

    @InjectMocks
    private AiAdvisoryController aiAdvisoryController;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        mockMvc = MockMvcBuilders.standaloneSetup(aiAdvisoryController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    @DisplayName("POST /api/v1/ai/predict returns 200 with prediction payload")
    void testPredictPriceSuccess() throws Exception {
        ModelAppPredictionResponse response = ModelAppPredictionResponse.builder()
                .market("Bareilly")
                .commodity("Onion")
                .currentPrice(1850.0)
                .predictedPrice(1920.0)
                .expectedDirection("UP")
                .build();

        when(aiAdvisoryService.predictPrice(any())).thenReturn(response);

        ModelAppPredictionRequest request = ModelAppPredictionRequest.builder()
                .market("Bareilly")
                .commodity("Onion")
                .currentPrice(1850.0)
                .build();

        mockMvc.perform(post("/api/v1/ai/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.market").value("Bareilly"))
                .andExpect(jsonPath("$.data.predicted_price").value(1920.0));
    }

    @Test
    @DisplayName("POST /api/v1/ai/recommend returns 200 with recommendations")
    void testGetRecommendationSuccess() throws Exception {
        ModelAppRecommendationResponse response = ModelAppRecommendationResponse.builder()
                .commodity("Onion")
                .recommendedMandi("Bareilly")
                .totalMandisEvaluated(1)
                .recommendations(List.of())
                .build();

        when(aiAdvisoryService.getMandiRecommendation(any())).thenReturn(response);

        ModelAppRecommendationRequest request = ModelAppRecommendationRequest.builder()
                .farmerLatitude(28.6139)
                .farmerLongitude(77.2090)
                .quantityQuintals(10.0)
                .commodity("Onion")
                .build();

        mockMvc.perform(post("/api/v1/ai/recommend")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.recommended_mandi").value("Bareilly"));
    }

    @Test
    @DisplayName("POST /api/v1/ai/recommend/async returns 202 Accepted with job metadata")
    void testSubmitAsyncRecommendationSuccess() throws Exception {
        ModelAppAsyncJobAcceptedResponse response = ModelAppAsyncJobAcceptedResponse.builder()
                .jobId("job-uuid-12345")
                .status("QUEUED")
                .operation("RECOMMEND_MANDI")
                .pollUrl("/api/v1/jobs/job-uuid-12345")
                .build();

        when(aiAdvisoryService.submitAsyncRecommendation(any())).thenReturn(response);

        ModelAppRecommendationRequest request = ModelAppRecommendationRequest.builder()
                .farmerLatitude(28.6139)
                .farmerLongitude(77.2090)
                .quantityQuintals(10.0)
                .commodity("Onion")
                .build();

        mockMvc.perform(post("/api/v1/ai/recommend/async")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.job_id").value("job-uuid-12345"))
                .andExpect(jsonPath("$.data.status").value("QUEUED"));
    }

    @Test
    @DisplayName("GET /api/v1/ai/jobs/{jobId} returns 200 with job status")
    void testGetJobStatusSuccess() throws Exception {
        ModelAppJobStatusResponse response = ModelAppJobStatusResponse.builder()
                .jobId("job-uuid-12345")
                .operation("RECOMMEND_MANDI")
                .status("COMPLETED")
                .result(Map.of("recommended_mandi", "Bareilly"))
                .build();

        when(aiAdvisoryService.getJobStatus("job-uuid-12345")).thenReturn(response);

        mockMvc.perform(get("/api/v1/ai/jobs/job-uuid-12345"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.status").value("COMPLETED"))
                .andExpect(jsonPath("$.data.result.recommended_mandi").value("Bareilly"));
    }

    @Test
    @DisplayName("POST /api/v1/ai/query returns 200 with routed query response")
    void testProcessNaturalLanguageQuerySuccess() throws Exception {
        com.marketlink.backend.ai.dto.query.AiQueryResponse response =
                com.marketlink.backend.ai.dto.query.AiQueryResponse.builder()
                        .intent(com.marketlink.backend.ai.enums.AiQueryIntent.PRICE_PREDICTION)
                        .confidence(0.92)
                        .answer("Predicted price for Onion is ₹1,920/quintal")
                        .build();

        when(aiAdvisoryService.routeNaturalLanguageQuery(any())).thenReturn(response);

        com.marketlink.backend.ai.dto.query.AiNaturalLanguageQueryRequest request =
                com.marketlink.backend.ai.dto.query.AiNaturalLanguageQueryRequest.builder()
                        .query("What price can I expect for onions next week?")
                        .crop("Onion")
                        .build();

        mockMvc.perform(post("/api/v1/ai/query")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.type").value("PRICE_PREDICTION"))
                .andExpect(jsonPath("$.data.answer").value("Predicted price for Onion is ₹1,920/quintal"));
    }

    @Test
    @DisplayName("GET /api/v1/ai/health returns 200")
    void testCheckHealthSuccess() throws Exception {
        ModelAppHealthResponse response = ModelAppHealthResponse.builder()
                .status("HEALTHY")
                .service("marketlink-ai")
                .build();

        when(aiAdvisoryService.checkHealth()).thenReturn(response);

        mockMvc.perform(get("/api/v1/ai/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.status").value("HEALTHY"));
    }

    @Test
    @DisplayName("GET /api/v1/ai/ready returns 200 when ready and 503 when not ready")
    void testCheckReadiness() throws Exception {
        ModelAppReadinessResponse readyResponse = ModelAppReadinessResponse.builder()
                .ready(true)
                .status("READY")
                .build();

        when(aiAdvisoryService.checkReadiness()).thenReturn(readyResponse);

        mockMvc.perform(get("/api/v1/ai/ready"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.ready").value(true));

        ModelAppReadinessResponse unreadyResponse = ModelAppReadinessResponse.builder()
                .ready(false)
                .status("NOT_READY")
                .build();

        when(aiAdvisoryService.checkReadiness()).thenReturn(unreadyResponse);

        mockMvc.perform(get("/api/v1/ai/ready"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.data.ready").value(false));
    }

    @Test
    @DisplayName("404 JobNotFoundException translates cleanly via GlobalExceptionHandler")
    void testJobNotFoundExceptionMapping() throws Exception {
        when(aiAdvisoryService.getJobStatus("non-existent-id"))
                .thenThrow(new ModelAppNotFoundException("Job non-existent-id not found"));

        mockMvc.perform(get("/api/v1/ai/jobs/non-existent-id"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.message").value("Job non-existent-id not found"));
    }

    @Test
    @DisplayName("503 ModelAppUnavailableException translates cleanly via GlobalExceptionHandler")
    void testModelAppUnavailableExceptionMapping() throws Exception {
        when(aiAdvisoryService.predictPrice(any()))
                .thenThrow(new ModelAppUnavailableException("Model-app connection refused"));

        ModelAppPredictionRequest request = ModelAppPredictionRequest.builder()
                .market("Bareilly")
                .commodity("Onion")
                .currentPrice(1850.0)
                .build();

        mockMvc.perform(post("/api/v1/ai/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.status").value(503))
                .andExpect(jsonPath("$.message").value("Model-app connection refused"));
    }
}
