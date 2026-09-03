package com.agri.voice.voice.audio;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Base64;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.agri.voice.voice.VoiceSession;
import com.agri.voice.voice.audio.AudioFrameDecoder.DecodeError;
import com.agri.voice.voice.audio.AudioFrameDecoder.DecodeResult;
import com.agri.voice.voice.dto.MediaEvent;

class AudioFrameDecoderTest {

    private static final Instant NOW = Instant.parse("2026-09-03T00:00:00Z");

    private AudioFrameDecoder decoder;
    private VoiceSession session;

    @BeforeEach
    void setUp() {
        decoder = new AudioFrameDecoder(Clock.fixed(NOW, ZoneOffset.UTC));
        session = new VoiceSession("transport-1", NOW.minusSeconds(1));
        session.start(new VoiceSession.StartDetails(
                "CA-test",
                "MZ-test",
                "AC-test",
                "+919999999999",
                "+918888888888",
                new VoiceSession.MediaFormat("audio/x-raw", 16_000, 1, 16)), NOW);
    }

    @Test
    void decodesValidBase64PcmAndCreatesFrameMetadata() {
        byte[] pcm = new byte[320];
        pcm[0] = 42;
        MediaEvent event = mediaEvent("3", "2", "200", Base64.getEncoder().encodeToString(pcm));

        DecodeResult result = decoder.decode(event, session);

        assertThat(result.successful()).isTrue();
        AudioFrame frame = result.frame();
        assertThat(frame.pcm16LittleEndian()).containsExactly(pcm);
        assertThat(frame.streamSid()).isEqualTo("MZ-test");
        assertThat(frame.sequenceNumber()).isEqualTo(3);
        assertThat(frame.chunkNumber()).isEqualTo(2);
        assertThat(frame.timestampMilliseconds()).isEqualTo(200);
        assertThat(frame.receivedAt()).isEqualTo(NOW);
        assertThat(frame.sampleRate()).isEqualTo(16_000);
        assertThat(frame.channels()).isEqualTo(1);
        assertThat(frame.bitsPerSample()).isEqualTo(16);
        assertThat(frame.byteLength()).isEqualTo(320);
    }

    @Test
    void rejectsInvalidBase64() {
        DecodeResult result = decoder.decode(mediaEvent("3", "2", "200", "not-base64%%%"), session);

        assertThat(result.successful()).isFalse();
        assertThat(result.error()).isEqualTo(DecodeError.INVALID_BASE64);
    }

    @Test
    void rejectsMisalignedPcmFrame() {
        String payload = Base64.getEncoder().encodeToString(new byte[318]);

        DecodeResult result = decoder.decode(mediaEvent("3", "2", "200", payload), session);

        assertThat(result.error()).isEqualTo(DecodeError.INVALID_SIZE);
    }

    @Test
    void rejectsInvalidNumericMetadata() {
        String payload = Base64.getEncoder().encodeToString(new byte[320]);

        DecodeResult result = decoder.decode(mediaEvent("three", "2", "200", payload), session);

        assertThat(result.error()).isEqualTo(DecodeError.INVALID_METADATA);
    }

    @Test
    void rejectsMediaForDifferentStream() {
        String payload = Base64.getEncoder().encodeToString(new byte[320]);
        MediaEvent event = new MediaEvent(
                "media", "3", "MZ-other", new MediaEvent.MediaPayload("2", "200", payload));

        DecodeResult result = decoder.decode(event, session);

        assertThat(result.error()).isEqualTo(DecodeError.STREAM_MISMATCH);
    }

    private MediaEvent mediaEvent(String sequence, String chunk, String timestamp, String payload) {
        return new MediaEvent(
                "media",
                sequence,
                "MZ-test",
                new MediaEvent.MediaPayload(chunk, timestamp, payload));
    }
}
