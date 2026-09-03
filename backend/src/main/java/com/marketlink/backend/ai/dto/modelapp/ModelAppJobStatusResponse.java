package com.marketlink.backend.ai.dto.modelapp;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * DTO matching Model-app JobStatusResponse schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppJobStatusResponse {

    @JsonProperty("job_id")
    private String jobId;

    private String operation;
    private String status;

    @JsonProperty("created_at")
    private String createdAt;

    @JsonProperty("updated_at")
    private String updatedAt;

    @JsonProperty("completed_at")
    private String completedAt;

    private Map<String, Object> result;
    private String error;
}
