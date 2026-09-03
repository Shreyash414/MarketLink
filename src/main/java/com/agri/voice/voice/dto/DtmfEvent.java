package com.agri.voice.voice.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public record DtmfEvent(
        String event,
        @JsonProperty("sequence_number") String sequenceNumber,
        @JsonProperty("stream_sid") String streamSid,
        DtmfPayload dtmf) implements ExotelEvent {

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record DtmfPayload(String digit, String duration) {
    }
}
