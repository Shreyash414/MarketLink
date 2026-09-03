package com.marketlink.backend.ai.exception;

import com.marketlink.backend.common.exception.ApiException;
import org.springframework.http.HttpStatus;

/**
 * Base domain exception for all failures originating from or communicating with Model-app.
 */
public class ModelAppException extends ApiException {

    public ModelAppException(String message, HttpStatus status) {
        super(message, status);
    }

    public ModelAppException(String message, HttpStatus status, Throwable cause) {
        super(message, status);
        if (cause != null) {
            initCause(cause);
        }
    }
}
