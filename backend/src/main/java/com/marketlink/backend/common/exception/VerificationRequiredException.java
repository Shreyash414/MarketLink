package com.marketlink.backend.common.exception;

import org.springframework.http.HttpStatus;

public class VerificationRequiredException extends ApiException {
    public VerificationRequiredException(String message) {
        super(message, HttpStatus.FORBIDDEN);
    }
}
