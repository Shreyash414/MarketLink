package com.agri.voice.ai.llm;

import java.util.concurrent.CompletableFuture;

public interface LLMService {

    CompletableFuture<LLMResponse> generate(LLMRequest request);
}
