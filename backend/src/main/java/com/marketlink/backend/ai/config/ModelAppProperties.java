package com.marketlink.backend.ai.config;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;
import org.springframework.validation.annotation.Validated;

/**
 * Configuration properties for external FastAPI Model-app integration.
 */
@Data
@Validated
@Configuration
@ConfigurationProperties(prefix = "marketlink.model-app")
public class ModelAppProperties {

    /**
     * Base URL of the FastAPI Model-app (e.g. http://localhost:8000).
     */
    @NotBlank(message = "Model-app base URL must not be blank")
    private String baseUrl = "http://localhost:8000";

    /**
     * Connection timeout in milliseconds.
     */
    @Positive(message = "Connect timeout must be positive")
    private int connectTimeoutMs = 5000;

    /**
     * Read/Response timeout in milliseconds for standard predictions and recommendations.
     */
    @Positive(message = "Read timeout must be positive")
    private int readTimeoutMs = 15000;

    /**
     * Extended read timeout in milliseconds for natural language / Ollama queries.
     */
    @Positive(message = "Query timeout must be positive")
    private int queryTimeoutMs = 30000;
}
