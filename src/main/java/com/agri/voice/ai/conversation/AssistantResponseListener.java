package com.agri.voice.ai.conversation;

@FunctionalInterface
public interface AssistantResponseListener {

    void onResponse(AssistantResponse response);
}
