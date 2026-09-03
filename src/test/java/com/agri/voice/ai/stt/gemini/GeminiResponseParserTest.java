package com.agri.voice.ai.stt.gemini;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

import com.agri.voice.ai.stt.TranscriptType;
import com.fasterxml.jackson.databind.ObjectMapper;

class GeminiResponseParserTest {

    private final GeminiResponseParser parser = new GeminiResponseParser(new ObjectMapper());

    @Test
    void parsesInterimTranscription() {
        var result = parser.parse("""
                {"serverContent":{"interimInputTranscription":{"text":"गेहूं का भाव"}}}
                """);

        assertThat(result.successful()).isTrue();
        assertThat(result.transcripts()).singleElement().satisfies(transcript -> {
            assertThat(transcript.text()).isEqualTo("गेहूं का भाव");
            assertThat(transcript.type()).isEqualTo(TranscriptType.INTERIM);
        });
    }

    @Test
    void parsesFinalTranscription() {
        var result = parser.parse("""
                {"serverContent":{"inputTranscription":{"text":"मंडी में wheat price"}}}
                """);

        assertThat(result.transcripts()).singleElement().satisfies(transcript -> {
            assertThat(transcript.text()).isEqualTo("मंडी में wheat price");
            assertThat(transcript.type()).isEqualTo(TranscriptType.FINAL);
        });
    }

    @Test
    void recognizesSetupCompletion() {
        var result = parser.parse("{\"setupComplete\":{}}");

        assertThat(result.successful()).isTrue();
        assertThat(result.setupComplete()).isTrue();
        assertThat(result.transcripts()).isEmpty();
        assertThat(result.topLevelFields()).containsExactly("setupComplete");
        assertThat(result.serverContentFields()).isEmpty();
    }

    @Test
    void reportsSafeProtocolShapeAndProviderErrorWithoutChangingTranscriptParsing() {
        var result = parser.parse("""
                {
                  "serverContent": {
                    "interimInputTranscription": {"text": "partial"},
                    "inputTranscription": {"text": "final"},
                    "turnComplete": true
                  },
                  "error": {
                    "code": 400,
                    "status": "INVALID_ARGUMENT",
                    "message": "diagnostic"
                  }
                }
                """);

        assertThat(result.successful()).isTrue();
        assertThat(result.topLevelFields()).containsExactly("serverContent", "error");
        assertThat(result.serverContentFields())
                .containsExactly("interimInputTranscription", "inputTranscription", "turnComplete");
        assertThat(result.transcripts()).hasSize(2);
        assertThat(result.providerError())
                .isEqualTo(new GeminiResponseParser.ProviderError(400, "INVALID_ARGUMENT", "diagnostic"));
    }

    @Test
    void malformedResponseIsRejectedWithoutAnException() {
        assertThat(parser.parse("{broken").successful()).isFalse();
        assertThat(parser.parse("[]").successful()).isFalse();
        assertThat(parser.parse(null).successful()).isFalse();
    }
}
