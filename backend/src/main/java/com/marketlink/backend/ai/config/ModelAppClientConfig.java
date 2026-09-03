package com.marketlink.backend.ai.config;

import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.time.Duration;

/**
 * Spring configuration providing RestClient beans tailored for Model-app communication.
 */
@Configuration
@RequiredArgsConstructor
public class ModelAppClientConfig {

    private final ModelAppProperties properties;

    @Bean
    public RestClient.Builder modelAppRestClientBuilder() {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout((int) Duration.ofMillis(properties.getConnectTimeoutMs()).toMillis());
        requestFactory.setReadTimeout((int) Duration.ofMillis(properties.getReadTimeoutMs()).toMillis());

        return RestClient.builder()
                .baseUrl(properties.getBaseUrl())
                .requestFactory(requestFactory);
    }

    @Bean
    public RestClient modelAppRestClient(RestClient.Builder modelAppRestClientBuilder) {
        return modelAppRestClientBuilder.build();
    }
}
