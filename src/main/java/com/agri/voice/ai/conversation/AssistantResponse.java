package com.agri.voice.ai.conversation;

import com.agri.voice.ai.llm.LLMResponse;

public record AssistantResponse(
        String conversationId,
        String text,
        boolean fallback,
        LLMResponse.Status status) {
}
