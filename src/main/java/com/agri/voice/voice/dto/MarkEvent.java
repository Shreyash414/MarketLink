package com.agri.voice.voice.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public record MarkEvent(
        String event,
        @JsonProperty("sequence_number") String sequenceNumber,
        @JsonProperty("stream_sid") String streamSid,
        MarkPayload mark) implements ExotelEvent {

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record MarkPayload(String name) {
    }
}
