package com.agri.voice.voice.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public record MediaEvent(
        String event,
        @JsonProperty("sequence_number") String sequenceNumber,
        @JsonProperty("stream_sid") String streamSid,
        MediaPayload media) implements ExotelEvent {

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record MediaPayload(String chunk, String timestamp, String payload) {
    }
}
