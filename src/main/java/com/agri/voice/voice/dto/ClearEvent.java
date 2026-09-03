package com.agri.voice.voice.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public record ClearEvent(
        String event,
        @JsonProperty("stream_sid") String streamSid) implements ExotelEvent {
}
