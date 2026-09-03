package com.marketlink.backend.ai.exception;

import org.springframework.http.HttpStatus;

/**
 * Thrown when an HTTP connection or read timeout occurs communicating with Model-app.
 */
public class ModelAppTimeoutException extends ModelAppException {

    public ModelAppTimeoutException(String message) {
        super(message, HttpStatus.GATEWAY_TIMEOUT);
    }

    public ModelAppTimeoutException(String message, Throwable cause) {
        super(message, HttpStatus.GATEWAY_TIMEOUT, cause);
    }
}
