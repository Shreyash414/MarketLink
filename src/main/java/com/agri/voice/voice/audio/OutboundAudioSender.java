package com.agri.voice.voice.audio;

import java.io.IOException;

/**
 * Future outbound boundary for sending PCM audio and playback controls to Exotel.
 * Phase 2 intentionally provides no implementation.
 */
public interface OutboundAudioSender {

    void sendPcm(String transportSessionId, String streamSid, byte[] pcm16LittleEndian) throws IOException;

    void sendMark(String transportSessionId, String streamSid, String markName) throws IOException;

    void clear(String transportSessionId, String streamSid) throws IOException;
}
