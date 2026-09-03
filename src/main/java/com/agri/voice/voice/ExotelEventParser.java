package com.agri.voice.voice;

import org.springframework.stereotype.Component;

import com.agri.voice.voice.dto.ClearEvent;
import com.agri.voice.voice.dto.ConnectedEvent;
import com.agri.voice.voice.dto.DtmfEvent;
import com.agri.voice.voice.dto.ExotelEvent;
import com.agri.voice.voice.dto.MarkEvent;
import com.agri.voice.voice.dto.MediaEvent;
import com.agri.voice.voice.dto.StartEvent;
import com.agri.voice.voice.dto.StopEvent;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

@Component
public class ExotelEventParser {

    private final ObjectMapper objectMapper;

    public ExotelEventParser(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public ParseResult parse(String json) {
        if (json == null || json.isBlank()) {
            return ParseResult.failure(ParseError.MALFORMED_JSON);
        }

        try {
            JsonNode root = objectMapper.readTree(json);
            if (root == null || !root.isObject()) {
                return ParseResult.failure(ParseError.INVALID_ENVELOPE);
            }

            JsonNode eventNode = root.get("event");
            if (eventNode == null || eventNode.isNull() || !eventNode.isTextual()
                    || eventNode.asText().isBlank()) {
                return ParseResult.failure(ParseError.MISSING_EVENT);
            }

            return ExotelEventType.fromWireValue(eventNode.asText())
                    .map(type -> deserialize(type, root))
                    .orElseGet(() -> ParseResult.failure(ParseError.UNKNOWN_EVENT));
        } catch (JsonProcessingException | IllegalArgumentException exception) {
            return ParseResult.failure(ParseError.MALFORMED_JSON);
        }
    }

    private ParseResult deserialize(ExotelEventType type, JsonNode root) {
        try {
            ExotelEvent event = switch (type) {
                case CONNECTED -> objectMapper.treeToValue(root, ConnectedEvent.class);
                case START -> objectMapper.treeToValue(root, StartEvent.class);
                case MEDIA -> objectMapper.treeToValue(root, MediaEvent.class);
                case DTMF -> objectMapper.treeToValue(root, DtmfEvent.class);
                case STOP -> objectMapper.treeToValue(root, StopEvent.class);
                case MARK -> objectMapper.treeToValue(root, MarkEvent.class);
                case CLEAR -> objectMapper.treeToValue(root, ClearEvent.class);
            };
            return ParseResult.success(type, event);
        } catch (JsonProcessingException | IllegalArgumentException exception) {
            return ParseResult.failure(ParseError.INVALID_EVENT);
        }
    }

    public enum ParseError {
        MALFORMED_JSON,
        INVALID_ENVELOPE,
        MISSING_EVENT,
        UNKNOWN_EVENT,
        INVALID_EVENT
    }

    public record ParseResult(ExotelEventType type, ExotelEvent event, ParseError error) {

        public static ParseResult success(ExotelEventType type, ExotelEvent event) {
            return new ParseResult(type, event, null);
        }

        public static ParseResult failure(ParseError error) {
            return new ParseResult(null, null, error);
        }

        public boolean successful() {
            return type != null && event != null && error == null;
        }
    }
}
