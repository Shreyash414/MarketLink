package com.agri.voice.ai.stt.gemini;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;

class GeminiSttPropertiesTest {

    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
            .withUserConfiguration(TestConfiguration.class);

    @Test
    void loadsEnvironmentStyleConfigurationWithoutRequiringAKey() {
        contextRunner.withPropertyValues(
                        "gemini.stt.model=gemini-3.5-transcribe-live",
                        "gemini.stt.sample-rate=16000",
                        "gemini.stt.mode=SMART",
                        "gemini.stt.language-codes=",
                        "gemini.stt.custom-vocabulary=mandi,MSP,गेहूं",
                        "gemini.stt.queue-capacity=7")
                .run(context -> {
                    GeminiSttProperties properties = context.getBean(GeminiSttProperties.class);
                    assertThat(properties.getApiKey()).isEmpty();
                    assertThat(properties.getModel()).isEqualTo("gemini-3.5-transcribe-live");
                    assertThat(properties.getMode()).isEqualTo("SMART");
                    assertThat(properties.getLanguageCodes()).isEmpty();
                    assertThat(properties.getCustomVocabulary()).containsExactly("mandi", "MSP", "गेहूं");
                    assertThat(properties.getQueueCapacity()).isEqualTo(7);
                });
    }

    @Configuration(proxyBeanMethods = false)
    @EnableConfigurationProperties(GeminiSttProperties.class)
    static class TestConfiguration {
    }
}
