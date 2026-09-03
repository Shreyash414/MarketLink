package com.marketlink.backend.ai.exception;

import org.springframework.http.HttpStatus;

/**
 * Thrown when Model-app returns a 404 Not Found (e.g., job ID not found).
 */
public class ModelAppNotFoundException extends ModelAppException {

    public ModelAppNotFoundException(String message) {
        super(message, HttpStatus.NOT_FOUND);
    }

    public ModelAppNotFoundException(String message, Throwable cause) {
        super(message, HttpStatus.NOT_FOUND, cause);
    }
}
