package com.agri.voice.ai.stt.audio;

import java.util.Set;

import org.springframework.stereotype.Component;

import com.agri.voice.voice.audio.AudioFrame;

@Component
public final class Pcm16AudioNormalizer {

    public static final int TARGET_SAMPLE_RATE = 16_000;
    private static final Set<Integer> SUPPORTED_SAMPLE_RATES = Set.of(8_000, 16_000, 24_000);

    public byte[] normalize(AudioFrame frame) {
        if (frame == null) {
            throw new AudioNormalizationException("audio frame is required");
        }
        if (frame.channels() != 1 || frame.bitsPerSample() != 16) {
            throw new AudioNormalizationException("audio must be mono PCM16");
        }
        if (!SUPPORTED_SAMPLE_RATES.contains(frame.sampleRate())) {
            throw new AudioNormalizationException("unsupported sample rate");
        }

        byte[] input = frame.pcm16LittleEndian();
        if (input.length == 0 || input.length % 2 != 0) {
            throw new AudioNormalizationException("audio must contain complete PCM16 samples");
        }
        if (frame.sampleRate() == TARGET_SAMPLE_RATE) {
            return input;
        }

        short[] samples = decodeLittleEndian(input);
        int outputLength = Math.max(1,
                (int) Math.round(samples.length * (double) TARGET_SAMPLE_RATE / frame.sampleRate()));
        byte[] output = new byte[outputLength * 2];
        double sourceStep = (double) frame.sampleRate() / TARGET_SAMPLE_RATE;

        for (int outputIndex = 0; outputIndex < outputLength; outputIndex++) {
            double sourcePosition = outputIndex * sourceStep;
            int lowerIndex = Math.min((int) sourcePosition, samples.length - 1);
            int upperIndex = Math.min(lowerIndex + 1, samples.length - 1);
            double fraction = sourcePosition - lowerIndex;
            int interpolated = (int) Math.round(
                    samples[lowerIndex] + (samples[upperIndex] - samples[lowerIndex]) * fraction);
            writeLittleEndian(output, outputIndex * 2, (short) interpolated);
        }
        return output;
    }

    private short[] decodeLittleEndian(byte[] input) {
        short[] samples = new short[input.length / 2];
        for (int index = 0; index < samples.length; index++) {
            int low = input[index * 2] & 0xff;
            int high = input[index * 2 + 1];
            samples[index] = (short) ((high << 8) | low);
        }
        return samples;
    }

    private void writeLittleEndian(byte[] output, int offset, short sample) {
        output[offset] = (byte) (sample & 0xff);
        output[offset + 1] = (byte) ((sample >>> 8) & 0xff);
    }
}
