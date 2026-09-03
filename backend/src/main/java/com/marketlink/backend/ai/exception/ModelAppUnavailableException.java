package com.marketlink.backend.ai.exception;

import org.springframework.http.HttpStatus;

/**
 * Thrown when Model-app is unreachable, offline, or connection is refused.
 */
public class ModelAppUnavailableException extends ModelAppException {

    public ModelAppUnavailableException(String message) {
        super(message, HttpStatus.SERVICE_UNAVAILABLE);
    }

    public ModelAppUnavailableException(String message, Throwable cause) {
        super(message, HttpStatus.SERVICE_UNAVAILABLE, cause);
    }
}
