package com.marketlink.backend.verification.provider;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.UUID;

@Slf4j
@Component
public class MockUidaiVerificationAdapter implements UidaiVerificationProvider {

    @Value("${marketlink.security.uidai.valid-test-otp:123456}")
    private String validTestOtp;

    @Override
    public UidaiInitiationResult initiate(String aadhaarReference, boolean consent) {
        if (!consent) {
            return UidaiInitiationResult.builder()
                    .initiated(false)
                    .message("UIDAI consent was not provided.")
                    .build();
        }

        String transactionId = "UIDAI-TXN-" + UUID.randomUUID().toString().substring(0, 18).toUpperCase();
        String maskedHash = computeSafeHash(aadhaarReference);

        log.info("UIDAI verification initiated successfully. TxnId: {}", transactionId);

        return UidaiInitiationResult.builder()
                .transactionId(transactionId)
                .initiated(true)
                .message("OTP sent to Aadhaar-linked mobile number.")
                .maskedReferenceHash(maskedHash)
                .build();
    }

    @Override
    public UidaiValidationResult validateOtp(String transactionId, String otp) {
        log.info("Validating UIDAI OTP for TxnId: {}", transactionId);

        if (validTestOtp.equals(otp)) {
            return UidaiValidationResult.builder()
                    .success(true)
                    .message("UIDAI biometric/OTP verification completed successfully.")
                    .verificationAuthCode("AUTH-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase())
                    .build();
        } else {
            return UidaiValidationResult.builder()
                    .success(false)
                    .message("Invalid OTP or UIDAI verification failed.")
                    .build();
        }
    }

    private String computeSafeHash(String input) {
        if (input == null) return "HASH-UNKNOWN";
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            return "HASH-" + HexFormat.of().formatHex(hash).substring(0, 16);
        } catch (NoSuchAlgorithmException e) {
            return "HASH-" + Math.abs(input.hashCode());
        }
    }
}
