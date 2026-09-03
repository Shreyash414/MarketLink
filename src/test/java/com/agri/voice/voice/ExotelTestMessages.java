package com.agri.voice.voice;

import java.util.Base64;

final class ExotelTestMessages {

    static final String CALL_SID = "CA-test-call";
    static final String STREAM_SID = "MZ-test-stream";

    private ExotelTestMessages() {
    }

    static String connected() {
        return """
                {"event":"connected"}
                """;
    }

    static String start(int sampleRate) {
        return """
                {
                  "event": "start",
                  "sequence_number": 1,
                  "stream_sid": "%s",
                  "start": {
                    "stream_sid": "%s",
                    "call_sid": "%s",
                    "account_sid": "AC-test-account",
                    "from": "+919999999999",
                    "to": "+918888888888",
                    "custom_parameters": {"language": "hi"},
                    "media_format": {
                      "encoding": "audio/x-raw",
                      "sample_rate": "%d",
                      "bit_rate": "16"
                    }
                  }
                }
                """.formatted(STREAM_SID, STREAM_SID, CALL_SID, sampleRate);
    }

    static String media(int sequenceNumber, int chunk, long timestamp, byte[] pcm) {
        return """
                {
                  "event": "media",
                  "sequence_number": %d,
                  "stream_sid": "%s",
                  "media": {
                    "chunk": %d,
                    "timestamp": "%d",
                    "payload": "%s"
                  }
                }
                """.formatted(
                sequenceNumber,
                STREAM_SID,
                chunk,
                timestamp,
                Base64.getEncoder().encodeToString(pcm));
    }

    static String dtmf() {
        return """
                {
                  "event": "dtmf",
                  "sequence_number": 4,
                  "stream_sid": "%s",
                  "dtmf": {"digit": "5", "duration": "100"}
                }
                """.formatted(STREAM_SID);
    }

    static String mark() {
        return """
                {
                  "event": "mark",
                  "sequence_number": 5,
                  "stream_sid": "%s",
                  "mark": {"name": "turn-1-end"}
                }
                """.formatted(STREAM_SID);
    }

    static String clear() {
        return """
                {"event":"clear","stream_sid":"%s"}
                """.formatted(STREAM_SID);
    }

    static String stop() {
        return """
                {
                  "event": "stop",
                  "sequence_number": 6,
                  "stream_sid": "%s",
                  "stop": {
                    "call_sid": "%s",
                    "account_sid": "AC-test-account",
                    "reason": "callended"
                  }
                }
                """.formatted(STREAM_SID, CALL_SID);
    }

    static byte[] pcmFrame() {
        return new byte[320];
    }
}
