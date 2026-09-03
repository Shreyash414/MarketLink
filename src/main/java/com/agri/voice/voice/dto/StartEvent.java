package com.agri.voice.voice.dto;

import java.util.Map;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public record StartEvent(
        String event,
        @JsonProperty("sequence_number") String sequenceNumber,
        @JsonProperty("stream_sid") String streamSid,
        StartPayload start) implements ExotelEvent {

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record StartPayload(
            @JsonProperty("stream_sid") String streamSid,
            @JsonProperty("call_sid") String callSid,
            @JsonProperty("account_sid") String accountSid,
            String from,
            String to,
            @JsonProperty("custom_parameters") Map<String, String> customParameters,
            @JsonProperty("media_format") MediaFormat mediaFormat) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record MediaFormat(
            String encoding,
            @JsonProperty("sample_rate") String sampleRate,
            @JsonProperty("bit_rate") String bitRate) {
    }
}
