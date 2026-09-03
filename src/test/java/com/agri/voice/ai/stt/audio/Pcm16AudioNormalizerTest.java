package com.agri.voice.ai.stt.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;

import org.junit.jupiter.api.Test;

import com.agri.voice.voice.audio.AudioFrame;

class Pcm16AudioNormalizerTest {

    private final Pcm16AudioNormalizer normalizer = new Pcm16AudioNormalizer();

    @Test
    void sixteenKilohertzPassesThroughWithoutChangingSamples() {
        byte[] pcm = pcm(0, 1_000, -1_000, 32_767, -32_768);

        byte[] normalized = normalizer.normalize(frame(pcm, 16_000));

        assertThat(normalized).containsExactly(pcm);
    }

    @Test
    void eightKilohertzIsUpsampledToSixteenKilohertz() {
        byte[] normalized = normalizer.normalize(frame(pcm(0, 1_000, 2_000, 3_000), 8_000));

        assertThat(normalized).hasSize(16);
        assertThat(sample(normalized, 0)).isZero();
        assertThat(sample(normalized, 1)).isEqualTo(500);
        assertThat(sample(normalized, 2)).isEqualTo(1_000);
    }

    @Test
    void twentyFourKilohertzIsDownsampledToSixteenKilohertz() {
        byte[] normalized = normalizer.normalize(frame(pcm(0, 600, 1_200, 1_800, 2_400, 3_000), 24_000));

        assertThat(normalized).hasSize(8);
        assertThat(sample(normalized, 0)).isZero();
        assertThat(sample(normalized, 1)).isEqualTo(900);
    }

    @Test
    void emptyAndMisalignedAudioAreRejected() {
        assertThatThrownBy(() -> normalizer.normalize(frame(new byte[0], 16_000)))
                .isInstanceOf(AudioNormalizationException.class);
        assertThatThrownBy(() -> normalizer.normalize(frame(new byte[3], 16_000)))
                .isInstanceOf(AudioNormalizationException.class);
    }

    @Test
    void unsupportedFormatIsRejected() {
        assertThatThrownBy(() -> normalizer.normalize(frame(pcm(1, 2), 44_100)))
                .isInstanceOf(AudioNormalizationException.class);
        AudioFrame stereo = new AudioFrame(
                pcm(1, 2), "stream", 1, 1, 0, Instant.EPOCH, "raw", 16_000, 2, 16);
        assertThatThrownBy(() -> normalizer.normalize(stereo))
                .isInstanceOf(AudioNormalizationException.class);
    }

    private AudioFrame frame(byte[] pcm, int sampleRate) {
        return new AudioFrame(pcm, "stream", 1, 1, 0, Instant.EPOCH, "raw", sampleRate, 1, 16);
    }

    private byte[] pcm(int... samples) {
        byte[] bytes = new byte[samples.length * 2];
        for (int index = 0; index < samples.length; index++) {
            bytes[index * 2] = (byte) (samples[index] & 0xff);
            bytes[index * 2 + 1] = (byte) ((samples[index] >>> 8) & 0xff);
        }
        return bytes;
    }

    private int sample(byte[] pcm, int index) {
        return (short) (((pcm[index * 2 + 1] & 0xff) << 8) | (pcm[index * 2] & 0xff));
    }
}
