package com.agri.voice.ai.stt;

import com.agri.voice.voice.audio.AudioFrame;

public interface SpeechToTextService {

    StartResult startSession(SttSessionContext context, TranscriptListener listener);

    AudioResult acceptAudio(String transportSessionId, AudioFrame frame);

    StopResult stopSession(String transportSessionId);

    enum StartResult {
        STARTING,
        DUPLICATE,
        DISABLED,
        MISSING_CREDENTIAL,
        INVALID_CONFIGURATION,
        REJECTED
    }

    enum AudioResult {
        ACCEPTED,
        BUFFERED,
        BACKPRESSURE,
        NO_SESSION,
        SESSION_CLOSED,
        INVALID_AUDIO
    }

    enum StopResult {
        STOPPED,
        NOT_FOUND
    }
}
