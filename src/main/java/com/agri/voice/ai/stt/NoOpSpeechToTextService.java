package com.agri.voice.ai.stt;

import com.agri.voice.voice.audio.AudioFrame;

public final class NoOpSpeechToTextService implements SpeechToTextService {

    public static final NoOpSpeechToTextService INSTANCE = new NoOpSpeechToTextService();

    private NoOpSpeechToTextService() {
    }

    @Override
    public StartResult startSession(SttSessionContext context, TranscriptListener listener) {
        return StartResult.DISABLED;
    }

    @Override
    public AudioResult acceptAudio(String transportSessionId, AudioFrame frame) {
        return AudioResult.NO_SESSION;
    }

    @Override
    public StopResult stopSession(String transportSessionId) {
        return StopResult.NOT_FOUND;
    }
}
