package com.agri.voice.ai.stt.audio;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class PcmChunkBufferTest {

    @Test
    void emitsOneHundredMillisecondChunksAndRetainsOnlyTheBoundedRemainder() {
        PcmChunkBuffer buffer = new PcmChunkBuffer();

        assertThat(buffer.append(new byte[1_000])).isEmpty();
        assertThat(buffer.pendingBytes()).isEqualTo(1_000);
        assertThat(buffer.append(new byte[5_400]))
                .hasSize(2)
                .allSatisfy(chunk -> assertThat(chunk).hasSize(3_200));
        assertThat(buffer.pendingBytes()).isZero();
    }

    @Test
    void drainReturnsOnlyTheFinalPartialChunkOnce() {
        PcmChunkBuffer buffer = new PcmChunkBuffer();
        buffer.append(new byte[640]);

        assertThat(buffer.drain()).hasSize(640);
        assertThat(buffer.drain()).isEmpty();
    }
}
