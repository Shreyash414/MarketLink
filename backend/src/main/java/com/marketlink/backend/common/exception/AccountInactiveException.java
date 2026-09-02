package com.marketlink.backend.common.exception;

import org.springframework.http.HttpStatus;

public class AccountInactiveException extends ApiException {
    public AccountInactiveException(String message) {
        super(message, HttpStatus.FORBIDDEN);
    }
}
