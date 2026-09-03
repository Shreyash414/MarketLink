package com.agri.voice.voice;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.agri.voice.voice.ExotelEventParser.ParseError;
import com.agri.voice.voice.ExotelEventParser.ParseResult;
import com.agri.voice.voice.dto.ClearEvent;
import com.agri.voice.voice.dto.ConnectedEvent;
import com.agri.voice.voice.dto.DtmfEvent;
import com.agri.voice.voice.dto.MarkEvent;
import com.agri.voice.voice.dto.MediaEvent;
import com.agri.voice.voice.dto.StartEvent;
import com.agri.voice.voice.dto.StopEvent;
import com.fasterxml.jackson.databind.ObjectMapper;

class ExotelEventParserTest {

    private ExotelEventParser parser;

    @BeforeEach
    void setUp() {
        parser = new ExotelEventParser(new ObjectMapper());
    }

    @Test
    void parsesConnectedEvent() {
        ParseResult result = parser.parse(ExotelTestMessages.connected());

        assertThat(result.successful()).isTrue();
        assertThat(result.type()).isEqualTo(ExotelEventType.CONNECTED);
        assertThat(result.event()).isInstanceOf(ConnectedEvent.class);
    }

    @Test
    void parsesStartEventAndCoercesNumericSequenceToString() {
        ParseResult result = parser.parse(ExotelTestMessages.start(16_000));

        assertThat(result.successful()).isTrue();
        assertThat(result.type()).isEqualTo(ExotelEventType.START);
        StartEvent event = (StartEvent) result.event();
        assertThat(event.sequenceNumber()).isEqualTo("1");
        assertThat(event.start().callSid()).isEqualTo(ExotelTestMessages.CALL_SID);
        assertThat(event.start().streamSid()).isEqualTo(ExotelTestMessages.STREAM_SID);
        assertThat(event.start().from()).isEqualTo("+919999999999");
        assertThat(event.start().to()).isEqualTo("+918888888888");
        assertThat(event.start().mediaFormat().encoding()).isEqualTo("audio/x-raw");
        assertThat(event.start().mediaFormat().sampleRate()).isEqualTo("16000");
    }

    @Test
    void parsesMediaEvent() {
        ParseResult result = parser.parse(ExotelTestMessages.media(3, 2, 200, ExotelTestMessages.pcmFrame()));

        assertThat(result.successful()).isTrue();
        assertThat(result.type()).isEqualTo(ExotelEventType.MEDIA);
        MediaEvent event = (MediaEvent) result.event();
        assertThat(event.media().chunk()).isEqualTo("2");
        assertThat(event.media().timestamp()).isEqualTo("200");
        assertThat(event.media().payload()).isNotBlank();
    }

    @Test
    void parsesDtmfEvent() {
        ParseResult result = parser.parse(ExotelTestMessages.dtmf());

        assertThat(result.successful()).isTrue();
        assertThat(result.type()).isEqualTo(ExotelEventType.DTMF);
        assertThat(((DtmfEvent) result.event()).dtmf().digit()).isEqualTo("5");
    }

    @Test
    void parsesStopEvent() {
        ParseResult result = parser.parse(ExotelTestMessages.stop());

        assertThat(result.successful()).isTrue();
        assertThat(result.type()).isEqualTo(ExotelEventType.STOP);
        StopEvent event = (StopEvent) result.event();
        assertThat(event.stop().reason()).isEqualTo("callended");
        assertThat(event.stop().callSid()).isEqualTo(ExotelTestMessages.CALL_SID);
    }

    @Test
    void parsesMarkEvent() {
        ParseResult result = parser.parse(ExotelTestMessages.mark());

        assertThat(result.successful()).isTrue();
        assertThat(result.type()).isEqualTo(ExotelEventType.MARK);
        assertThat(((MarkEvent) result.event()).mark().name()).isEqualTo("turn-1-end");
    }

    @Test
    void parsesClearEvent() {
        ParseResult result = parser.parse(ExotelTestMessages.clear());

        assertThat(result.successful()).isTrue();
        assertThat(result.type()).isEqualTo(ExotelEventType.CLEAR);
        assertThat(((ClearEvent) result.event()).streamSid()).isEqualTo(ExotelTestMessages.STREAM_SID);
    }

    @Test
    void rejectsMalformedJson() {
        ParseResult result = parser.parse("{not-json");

        assertThat(result.successful()).isFalse();
        assertThat(result.error()).isEqualTo(ParseError.MALFORMED_JSON);
    }

    @Test
    void rejectsUnknownEvent() {
        ParseResult result = parser.parse("{\"event\":\"future-event\"}");

        assertThat(result.successful()).isFalse();
        assertThat(result.error()).isEqualTo(ParseError.UNKNOWN_EVENT);
    }

    @Test
    void rejectsMissingEventField() {
        ParseResult result = parser.parse("{\"stream_sid\":\"MZ-test\"}");

        assertThat(result.successful()).isFalse();
        assertThat(result.error()).isEqualTo(ParseError.MISSING_EVENT);
    }

    @Test
    void parsesStructurallyIncompleteStartForSafeLifecycleValidation() {
        ParseResult result = parser.parse("{\"event\":\"start\",\"start\":{}}");

        assertThat(result.successful()).isTrue();
        assertThat(result.type()).isEqualTo(ExotelEventType.START);
        StartEvent event = (StartEvent) result.event();
        assertThat(event.start().callSid()).isNull();
        assertThat(event.start().mediaFormat()).isNull();
    }
}
