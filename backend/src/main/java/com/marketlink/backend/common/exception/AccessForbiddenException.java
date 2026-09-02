package com.marketlink.backend.common.exception;

import org.springframework.http.HttpStatus;

public class AccessForbiddenException extends ApiException {
    public AccessForbiddenException(String message) {
        super(message, HttpStatus.FORBIDDEN);
    }
}
