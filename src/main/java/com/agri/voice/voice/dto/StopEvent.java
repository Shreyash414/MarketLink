package com.agri.voice.voice.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public record StopEvent(
        String event,
        @JsonProperty("sequence_number") String sequenceNumber,
        @JsonProperty("stream_sid") String streamSid,
        StopPayload stop) implements ExotelEvent {

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record StopPayload(
            @JsonProperty("call_sid") String callSid,
            @JsonProperty("account_sid") String accountSid,
            String reason) {
    }
}
