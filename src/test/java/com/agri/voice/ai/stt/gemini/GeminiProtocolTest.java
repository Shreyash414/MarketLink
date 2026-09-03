package com.agri.voice.ai.stt.gemini;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

class GeminiProtocolTest {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final GeminiProtocol protocol = new GeminiProtocol(objectMapper);

    @Test
    void setupUsesOfficialLiveTranscriptionFields() throws Exception {
        GeminiSttProperties properties = new GeminiSttProperties();
        properties.setMode("SMART");
        properties.setLanguageCodes(List.of());
        properties.setCustomVocabulary(List.of("mandi", "MSP"));

        JsonNode setup = objectMapper.readTree(protocol.setup(properties)).get("setup");

        assertThat(setup.get("model").asText()).isEqualTo("models/gemini-3.5-transcribe-live");
        assertThat(setup.at("/generationConfig/responseModalities/0").asText()).isEqualTo("TEXT");
        assertThat(setup.at("/inputAudioTranscription/languageCodes").isArray()).isTrue();
        assertThat(setup.at("/inputAudioTranscription/languageCodes").isEmpty()).isTrue();
        assertThat(setup.at("/inputAudioTranscription/customVocabulary/0").asText()).isEqualTo("mandi");
        assertThat(setup.at("/inputAudioTranscription/mode").asText()).isEqualTo("SMART");
    }

    @Test
    void audioAndEndMessagesUseOfficialRealtimeInputFields() throws Exception {
        JsonNode audio = objectMapper.readTree(protocol.audio(new byte[] {1, 2, 3, 4}));
        JsonNode end = objectMapper.readTree(protocol.audioStreamEnd());

        assertThat(audio.at("/realtimeInput/audio/data").asText()).isEqualTo("AQIDBA==");
        assertThat(audio.at("/realtimeInput/audio/mimeType").asText())
                .isEqualTo("audio/pcm;rate=16000");
        assertThat(audio.get("realtimeInput").size()).isOne();
        assertThat(audio.at("/realtimeInput/audio").size()).isEqualTo(2);
        assertThat(end.at("/realtimeInput/audioStreamEnd").asBoolean()).isTrue();
    }
}
