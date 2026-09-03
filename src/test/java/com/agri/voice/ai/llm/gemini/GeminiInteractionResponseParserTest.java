package com.agri.voice.ai.llm.gemini;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.databind.ObjectMapper;

class GeminiInteractionResponseParserTest {

    private final GeminiInteractionResponseParser parser = new GeminiInteractionResponseParser(new ObjectMapper());

    @Test
    void extractsTextOnlyFromModelOutputSteps() {
        GeminiInteractionResponseParser.ParseResult result = parser.parse(bytes("""
                {"steps":[
                  {"type":"user_input","content":[{"type":"text","text":"secret user text"}]},
                  {"type":"model_output","content":[
                    {"type":"text","text":"Namaste "},
                    {"type":"image","uri":"ignored"},
                    {"type":"text","text":"kisan bhai."}
                  ]}
                ]}
                """));

        assertThat(result.status()).isEqualTo(GeminiInteractionResponseParser.ParseResult.Status.SUCCESS);
        assertThat(result.text()).isEqualTo("Namaste kisan bhai.");
    }

    @Test
    void reportsEmptyWhenThereIsNoModelText() {
        assertThat(parser.parse(bytes("{\"steps\":[]}")).status())
                .isEqualTo(GeminiInteractionResponseParser.ParseResult.Status.EMPTY);
        assertThat(parser.parse(new byte[0]).status())
                .isEqualTo(GeminiInteractionResponseParser.ParseResult.Status.EMPTY);
    }

    @Test
    void reportsMalformedForInvalidOrUnexpectedJson() {
        assertThat(parser.parse(bytes("not-json")).status())
                .isEqualTo(GeminiInteractionResponseParser.ParseResult.Status.MALFORMED);
        assertThat(parser.parse(bytes("{\"output\":[]}")).status())
                .isEqualTo(GeminiInteractionResponseParser.ParseResult.Status.MALFORMED);
    }

    private byte[] bytes(String value) {
        return value.getBytes(StandardCharsets.UTF_8);
    }
}
