package com.marketlink.backend.ai.dto.modelapp;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO matching Model-app GeneralQueryRequest schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ModelAppQueryRequest {

    @NotBlank(message = "Query text is required")
    @Size(min = 1, max = 2000, message = "Query text must be between 1 and 2000 characters")
    private String query;

    @Builder.Default
    private String language = "en";
}
