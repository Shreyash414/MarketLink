package com.agri.voice.voice;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.agri.voice.voice.audio.AudioFrame;

class VoiceSessionTest {

    private static final Instant OPENED_AT = Instant.parse("2026-09-03T00:00:00Z");
    private static final Instant STARTED_AT = OPENED_AT.plusSeconds(1);

    private VoiceSession session;

    @BeforeEach
    void setUp() {
        session = new VoiceSession("transport-1", OPENED_AT);
    }

    @Test
    void createsSessionInOpenState() {
        assertThat(session.transportSessionId()).isEqualTo("transport-1");
        assertThat(session.openedAt()).isEqualTo(OPENED_AT);
        assertThat(session.state()).isEqualTo(VoiceSession.State.OPEN);
        assertThat(session.frameCount()).isZero();
    }

    @Test
    void startsSessionAndStoresRequiredMetadata() {
        VoiceSession.StartResult result = session.start(startDetails(), STARTED_AT);

        assertThat(result).isEqualTo(VoiceSession.StartResult.STARTED);
        assertThat(session.callSid()).isEqualTo("CA-test");
        assertThat(session.streamSid()).isEqualTo("MZ-test");
        assertThat(session.caller()).isEqualTo("+919999999999");
        assertThat(session.destination()).isEqualTo("+918888888888");
        assertThat(session.mediaFormat()).isEqualTo(new VoiceSession.MediaFormat("raw", 8_000, 1, 16));
    }

    @Test
    void duplicateEquivalentStartIsIdempotent() {
        session.start(startDetails(), STARTED_AT);

        VoiceSession.StartResult duplicate = session.start(startDetails(), STARTED_AT.plusSeconds(1));

        assertThat(duplicate).isEqualTo(VoiceSession.StartResult.DUPLICATE);
        assertThat(session.startedAt()).isEqualTo(STARTED_AT);
    }

    @Test
    void recordsMultipleFramesWithoutRetainingRawAudio() {
        session.start(startDetails(), STARTED_AT);

        assertThat(session.recordFrame(frame(2, 1, 100))).isEqualTo(VoiceSession.FrameResult.RECORDED);
        assertThat(session.recordFrame(frame(3, 2, 200))).isEqualTo(VoiceSession.FrameResult.RECORDED);

        assertThat(session.frameCount()).isEqualTo(2);
        assertThat(session.totalAudioBytes()).isEqualTo(640);
        assertThat(session.lastFrameMetadata().sequenceNumber()).isEqualTo(3);
        assertThat(session.lastFrameMetadata().chunkNumber()).isEqualTo(2);
        assertThat(session.lastFrameMetadata().timestampMilliseconds()).isEqualTo(200);
        assertThat(session.lastFrameMetadata().byteLength()).isEqualTo(320);
    }

    @Test
    void duplicateStopIsSafe() {
        session.start(startDetails(), STARTED_AT);

        VoiceSession.StopResult first = session.stop("callended", STARTED_AT.plusSeconds(2));
        VoiceSession.StopResult duplicate = session.stop("callended", STARTED_AT.plusSeconds(3));

        assertThat(first).isEqualTo(VoiceSession.StopResult.STOPPED);
        assertThat(duplicate).isEqualTo(VoiceSession.StopResult.DUPLICATE);
        assertThat(session.state()).isEqualTo(VoiceSession.State.STOPPED);
    }

    @Test
    void unexpectedStopBeforeStartIsSafe() {
        VoiceSession.StopResult result = session.stop("stopped", OPENED_AT.plusSeconds(1));

        assertThat(result).isEqualTo(VoiceSession.StopResult.UNEXPECTED);
        assertThat(session.state()).isEqualTo(VoiceSession.State.STOPPED);
    }

    @Test
    void closeIsIdempotentAndReleasesPersonalAndFrameState() {
        session.start(startDetails(), STARTED_AT);
        session.recordFrame(frame(2, 1, 100));

        session.close();
        session.close();

        assertThat(session.state()).isEqualTo(VoiceSession.State.CLOSED);
        assertThat(session.caller()).isNull();
        assertThat(session.destination()).isNull();
        assertThat(session.accountSid()).isNull();
        assertThat(session.lastFrameMetadata()).isNull();
    }

    private VoiceSession.StartDetails startDetails() {
        return new VoiceSession.StartDetails(
                "CA-test",
                "MZ-test",
                "AC-test",
                "+919999999999",
                "+918888888888",
                new VoiceSession.MediaFormat("raw", 8_000, 1, 16));
    }

    private AudioFrame frame(long sequence, long chunk, long timestamp) {
        return new AudioFrame(
                new byte[320],
                "MZ-test",
                sequence,
                chunk,
                timestamp,
                STARTED_AT.plusMillis(timestamp),
                "raw",
                8_000,
                1,
                16);
    }
}
