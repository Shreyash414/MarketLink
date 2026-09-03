package com.agri.voice.ai.conversation;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "conversation")
public class ConversationProperties {

    private int maxMessages = 12;
    private int maxContextCharacters = 8_000;
    private int maxMessageCharacters = 2_000;
    private int duplicateWindowSize = 32;
    private String fallbackResponse = "I'm sorry, I couldn't process that right now. Please try again.";
    private String systemInstructionOverride = "";

    public int getMaxMessages() {
        return maxMessages;
    }

    public void setMaxMessages(int maxMessages) {
        this.maxMessages = maxMessages;
    }

    public int getMaxContextCharacters() {
        return maxContextCharacters;
    }

    public void setMaxContextCharacters(int maxContextCharacters) {
        this.maxContextCharacters = maxContextCharacters;
    }

    public int getMaxMessageCharacters() {
        return maxMessageCharacters;
    }

    public void setMaxMessageCharacters(int maxMessageCharacters) {
        this.maxMessageCharacters = maxMessageCharacters;
    }

    public int getDuplicateWindowSize() {
        return duplicateWindowSize;
    }

    public void setDuplicateWindowSize(int duplicateWindowSize) {
        this.duplicateWindowSize = duplicateWindowSize;
    }

    public String getFallbackResponse() {
        return fallbackResponse;
    }

    public void setFallbackResponse(String fallbackResponse) {
        this.fallbackResponse = fallbackResponse;
    }

    public String getSystemInstructionOverride() {
        return systemInstructionOverride;
    }

    public void setSystemInstructionOverride(String systemInstructionOverride) {
        this.systemInstructionOverride = systemInstructionOverride;
    }
}
