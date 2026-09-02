package com.marketlink.backend.verification.provider;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

public interface UidaiVerificationProvider {

    UidaiInitiationResult initiate(String aadhaarReference, boolean consent);

    UidaiValidationResult validateOtp(String transactionId, String otp);

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    class UidaiInitiationResult {
        private String transactionId;
        private boolean initiated;
        private String message;
        private String maskedReferenceHash;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    class UidaiValidationResult {
        private boolean success;
        private String message;
        private String verificationAuthCode;
    }
}
