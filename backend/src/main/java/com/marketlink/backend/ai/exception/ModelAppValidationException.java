package com.marketlink.backend.ai.exception;

import org.springframework.http.HttpStatus;

/**
 * Thrown when Model-app returns a 422 Unprocessable Content or 400 Bad Request error.
 */
public class ModelAppValidationException extends ModelAppException {

    public ModelAppValidationException(String message) {
        super(message, HttpStatus.UNPROCESSABLE_ENTITY);
    }

    public ModelAppValidationException(String message, Throwable cause) {
        super(message, HttpStatus.UNPROCESSABLE_ENTITY, cause);
    }
}
