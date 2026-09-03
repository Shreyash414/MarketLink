package com.marketlink.backend.ai.dto.modelapp;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO matching Model-app AsyncRecommendationResponse (HTTP 202 Accepted).
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppAsyncJobAcceptedResponse {

    @JsonProperty("job_id")
    private String jobId;

    private String status;
    private String operation;

    @JsonProperty("created_at")
    private String createdAt;

    private String message;

    @JsonProperty("poll_url")
    private String pollUrl;
}
