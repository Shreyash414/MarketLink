package com.agri.voice.voice.audio;

import java.time.Instant;
import java.util.Objects;

public record AudioFrame(
        byte[] pcm16LittleEndian,
        String streamSid,
        long sequenceNumber,
        long chunkNumber,
        long timestampMilliseconds,
        Instant receivedAt,
        String encoding,
        int sampleRate,
        int channels,
        int bitsPerSample) {

    public AudioFrame {
        Objects.requireNonNull(pcm16LittleEndian, "pcm16LittleEndian must not be null");
        Objects.requireNonNull(receivedAt, "receivedAt must not be null");
        pcm16LittleEndian = pcm16LittleEndian.clone();
    }

    @Override
    public byte[] pcm16LittleEndian() {
        return pcm16LittleEndian.clone();
    }

    public int byteLength() {
        return pcm16LittleEndian.length;
    }
}
