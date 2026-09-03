package com.agri.voice.voice.audio;

import java.time.Clock;
import java.time.Instant;
import java.util.Base64;

import org.springframework.stereotype.Component;

import com.agri.voice.voice.VoiceSession;
import com.agri.voice.voice.dto.MediaEvent;

@Component
public class AudioFrameDecoder {

    static final int MAX_DECODED_FRAME_BYTES = 100_000;
    static final int PCM_ALIGNMENT_BYTES = 320;
    private static final int MAX_BASE64_PAYLOAD_CHARACTERS = 133_340;

    private final Clock clock;

    public AudioFrameDecoder() {
        this(Clock.systemUTC());
    }

    AudioFrameDecoder(Clock clock) {
        this.clock = clock;
    }

    public DecodeResult decode(MediaEvent event, VoiceSession session) {
        if (session == null || session.state() != VoiceSession.State.STARTED
                || session.mediaFormat() == null) {
            return DecodeResult.failure(DecodeError.NO_ACTIVE_SESSION);
        }
        if (event == null || event.media() == null) {
            return DecodeResult.failure(DecodeError.MISSING_MEDIA);
        }
        if (!hasText(event.streamSid()) || !event.streamSid().equals(session.streamSid())) {
            return DecodeResult.failure(DecodeError.STREAM_MISMATCH);
        }

        String payload = event.media().payload();
        if (!hasText(payload)) {
            return DecodeResult.failure(DecodeError.MISSING_PAYLOAD);
        }
        if (payload.length() > MAX_BASE64_PAYLOAD_CHARACTERS) {
            return DecodeResult.failure(DecodeError.INVALID_SIZE);
        }

        byte[] decoded;
        try {
            decoded = Base64.getDecoder().decode(payload);
        } catch (IllegalArgumentException exception) {
            return DecodeResult.failure(DecodeError.INVALID_BASE64);
        }

        if (decoded.length == 0 || decoded.length > MAX_DECODED_FRAME_BYTES
                || decoded.length % PCM_ALIGNMENT_BYTES != 0) {
            return DecodeResult.failure(DecodeError.INVALID_SIZE);
        }

        Long sequenceNumber = parseNonNegative(event.sequenceNumber());
        Long chunkNumber = parseNonNegative(event.media().chunk());
        Long timestamp = parseNonNegative(event.media().timestamp());
        if (sequenceNumber == null || chunkNumber == null || timestamp == null) {
            return DecodeResult.failure(DecodeError.INVALID_METADATA);
        }

        VoiceSession.MediaFormat format = session.mediaFormat();
        AudioFrame frame = new AudioFrame(
                decoded,
                event.streamSid(),
                sequenceNumber,
                chunkNumber,
                timestamp,
                Instant.now(clock),
                format.encoding(),
                format.sampleRate(),
                format.channels(),
                format.bitsPerSample());
        return DecodeResult.success(frame);
    }

    private Long parseNonNegative(String value) {
        if (!hasText(value)) {
            return -1L;
        }
        try {
            long parsed = Long.parseLong(value);
            return parsed >= 0 ? parsed : null;
        } catch (NumberFormatException exception) {
            return null;
        }
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    public enum DecodeError {
        NO_ACTIVE_SESSION,
        MISSING_MEDIA,
        MISSING_PAYLOAD,
        STREAM_MISMATCH,
        INVALID_BASE64,
        INVALID_SIZE,
        INVALID_METADATA
    }

    public record DecodeResult(AudioFrame frame, DecodeError error) {

        public static DecodeResult success(AudioFrame frame) {
            return new DecodeResult(frame, null);
        }

        public static DecodeResult failure(DecodeError error) {
            return new DecodeResult(null, error);
        }

        public boolean successful() {
            return frame != null && error == null;
        }
    }
}
