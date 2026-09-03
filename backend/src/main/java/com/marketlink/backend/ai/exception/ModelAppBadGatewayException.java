package com.marketlink.backend.ai.exception;

import org.springframework.http.HttpStatus;

/**
 * Thrown when Model-app returns a 502 Bad Gateway (e.g., upstream Ollama LLM failure).
 */
public class ModelAppBadGatewayException extends ModelAppException {

    public ModelAppBadGatewayException(String message) {
        super(message, HttpStatus.BAD_GATEWAY);
    }

    public ModelAppBadGatewayException(String message, Throwable cause) {
        super(message, HttpStatus.BAD_GATEWAY, cause);
    }
}
