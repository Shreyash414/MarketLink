package com.agri.voice.ai.stt.audio;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public final class PcmChunkBuffer {

    public static final int DEFAULT_CHUNK_BYTES = 3_200;

    private final byte[] pending;
    private int size;

    public PcmChunkBuffer() {
        this(DEFAULT_CHUNK_BYTES);
    }

    public PcmChunkBuffer(int chunkBytes) {
        if (chunkBytes <= 0 || chunkBytes % 2 != 0) {
            throw new IllegalArgumentException("chunkBytes must be a positive PCM16-aligned value");
        }
        pending = new byte[chunkBytes];
    }

    public synchronized List<byte[]> append(byte[] audio) {
        if (audio == null || audio.length == 0 || audio.length % 2 != 0) {
            throw new AudioNormalizationException("normalized audio must contain PCM16 samples");
        }

        List<byte[]> chunks = new ArrayList<>();
        int sourceOffset = 0;
        while (sourceOffset < audio.length) {
            int copied = Math.min(pending.length - size, audio.length - sourceOffset);
            System.arraycopy(audio, sourceOffset, pending, size, copied);
            size += copied;
            sourceOffset += copied;
            if (size == pending.length) {
                chunks.add(pending.clone());
                size = 0;
            }
        }
        return chunks;
    }

    public synchronized byte[] drain() {
        if (size == 0) {
            return new byte[0];
        }
        byte[] finalChunk = Arrays.copyOf(pending, size);
        size = 0;
        return finalChunk;
    }

    public synchronized int pendingBytes() {
        return size;
    }
}
