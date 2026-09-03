package com.agri.voice.ai.stt;

@FunctionalInterface
public interface TranscriptListener {

    void onTranscript(Transcript transcript);
}
