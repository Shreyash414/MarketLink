package com.agri.voice.voice;

import java.time.Instant;
import java.util.Objects;

import com.agri.voice.voice.audio.AudioFrame;

public final class VoiceSession implements AutoCloseable {

    private final String transportSessionId;
    private final Instant openedAt;

    private State state = State.OPEN;
    private boolean connectedEventReceived;
    private String callSid;
    private String streamSid;
    private String accountSid;
    private String caller;
    private String destination;
    private MediaFormat mediaFormat;
    private Instant startedAt;
    private Instant stoppedAt;
    private String stopReason;
    private long frameCount;
    private long totalAudioBytes;
    private FrameMetadata lastFrameMetadata;

    public VoiceSession(String transportSessionId, Instant openedAt) {
        this.transportSessionId = requireText(transportSessionId, "transportSessionId");
        this.openedAt = Objects.requireNonNull(openedAt, "openedAt must not be null");
    }

    public synchronized ConnectedResult recordConnectedEvent() {
        if (state == State.CLOSED) {
            return ConnectedResult.CLOSED;
        }
        if (connectedEventReceived) {
            return ConnectedResult.DUPLICATE;
        }
        connectedEventReceived = true;
        return ConnectedResult.RECORDED;
    }

    public synchronized StartResult start(StartDetails details, Instant startTime) {
        Objects.requireNonNull(details, "details must not be null");
        Objects.requireNonNull(startTime, "startTime must not be null");

        if (state == State.CLOSED || state == State.STOPPED) {
            return StartResult.INVALID_STATE;
        }
        if (state == State.STARTED) {
            return matches(details) ? StartResult.DUPLICATE : StartResult.CONFLICT;
        }

        callSid = details.callSid();
        streamSid = details.streamSid();
        accountSid = details.accountSid();
        caller = details.caller();
        destination = details.destination();
        mediaFormat = details.mediaFormat();
        startedAt = startTime;
        state = State.STARTED;
        return StartResult.STARTED;
    }

    public synchronized FrameResult recordFrame(AudioFrame frame) {
        Objects.requireNonNull(frame, "frame must not be null");
        if (state != State.STARTED) {
            return FrameResult.INVALID_STATE;
        }
        if (!Objects.equals(streamSid, frame.streamSid())) {
            return FrameResult.STREAM_MISMATCH;
        }

        frameCount++;
        totalAudioBytes += frame.byteLength();
        lastFrameMetadata = new FrameMetadata(
                frame.sequenceNumber(),
                frame.chunkNumber(),
                frame.timestampMilliseconds(),
                frame.receivedAt(),
                frame.byteLength());
        return FrameResult.RECORDED;
    }

    public synchronized StopResult stop(String reason, Instant stopTime) {
        Objects.requireNonNull(stopTime, "stopTime must not be null");
        if (state == State.CLOSED || state == State.STOPPED) {
            return StopResult.DUPLICATE;
        }

        StopResult result = state == State.STARTED ? StopResult.STOPPED : StopResult.UNEXPECTED;
        stopReason = reason;
        stoppedAt = stopTime;
        state = State.STOPPED;
        return result;
    }

    @Override
    public synchronized void close() {
        if (state == State.CLOSED) {
            return;
        }

        state = State.CLOSED;
        caller = null;
        destination = null;
        accountSid = null;
        lastFrameMetadata = null;
    }

    private boolean matches(StartDetails details) {
        return Objects.equals(callSid, details.callSid())
                && Objects.equals(streamSid, details.streamSid())
                && Objects.equals(caller, details.caller())
                && Objects.equals(destination, details.destination())
                && Objects.equals(mediaFormat, details.mediaFormat());
    }

    public String transportSessionId() {
        return transportSessionId;
    }

    public Instant openedAt() {
        return openedAt;
    }

    public synchronized State state() {
        return state;
    }

    public synchronized boolean connectedEventReceived() {
        return connectedEventReceived;
    }

    public synchronized String callSid() {
        return callSid;
    }

    public synchronized String streamSid() {
        return streamSid;
    }

    public synchronized String accountSid() {
        return accountSid;
    }

    public synchronized String caller() {
        return caller;
    }

    public synchronized String destination() {
        return destination;
    }

    public synchronized MediaFormat mediaFormat() {
        return mediaFormat;
    }

    public synchronized Instant startedAt() {
        return startedAt;
    }

    public synchronized Instant stoppedAt() {
        return stoppedAt;
    }

    public synchronized String stopReason() {
        return stopReason;
    }

    public synchronized long frameCount() {
        return frameCount;
    }

    public synchronized long totalAudioBytes() {
        return totalAudioBytes;
    }

    public synchronized FrameMetadata lastFrameMetadata() {
        return lastFrameMetadata;
    }

    private static String requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
        return value;
    }

    public enum State {
        OPEN,
        STARTED,
        STOPPED,
        CLOSED
    }

    public enum ConnectedResult {
        RECORDED,
        DUPLICATE,
        CLOSED
    }

    public enum StartResult {
        STARTED,
        DUPLICATE,
        CONFLICT,
        INVALID_STATE
    }

    public enum FrameResult {
        RECORDED,
        STREAM_MISMATCH,
        INVALID_STATE
    }

    public enum StopResult {
        STOPPED,
        UNEXPECTED,
        DUPLICATE
    }

    public record StartDetails(
            String callSid,
            String streamSid,
            String accountSid,
            String caller,
            String destination,
            MediaFormat mediaFormat) {

        public StartDetails {
            requireText(callSid, "callSid");
            requireText(streamSid, "streamSid");
            requireText(caller, "caller");
            requireText(destination, "destination");
            Objects.requireNonNull(mediaFormat, "mediaFormat must not be null");
        }
    }

    public record MediaFormat(String encoding, int sampleRate, int channels, int bitsPerSample) {

        public MediaFormat {
            requireText(encoding, "encoding");
            if (sampleRate <= 0 || channels <= 0 || bitsPerSample <= 0) {
                throw new IllegalArgumentException("Audio format values must be positive");
            }
        }
    }

    public record FrameMetadata(
            long sequenceNumber,
            long chunkNumber,
            long timestampMilliseconds,
            Instant receivedAt,
            int byteLength) {
    }
}
