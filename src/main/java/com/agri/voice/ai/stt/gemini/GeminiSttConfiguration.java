package com.agri.voice.ai.stt.gemini;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(GeminiSttProperties.class)
public class GeminiSttConfiguration {
}
