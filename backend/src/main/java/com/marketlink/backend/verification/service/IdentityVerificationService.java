package com.marketlink.backend.verification.service;

import com.marketlink.backend.common.exception.AccountInactiveException;
import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.user.entity.UidaiVerificationRecord;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.AccountStatus;
import com.marketlink.backend.domain.user.enums.VerificationState;
import com.marketlink.backend.domain.user.repository.UidaiVerificationRecordRepository;
import com.marketlink.backend.domain.user.repository.UserRepository;
import com.marketlink.backend.verification.dto.UidaiStartRequest;
import com.marketlink.backend.verification.dto.UidaiStartResponse;
import com.marketlink.backend.verification.dto.UidaiVerifyOtpRequest;
import com.marketlink.backend.verification.dto.VerificationStatusResponse;
import com.marketlink.backend.verification.provider.UidaiVerificationProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class IdentityVerificationService {

    private final UserRepository userRepository;
    private final UidaiVerificationRecordRepository recordRepository;
    private final UidaiVerificationProvider verificationProvider;

    @Transactional
    public UidaiStartResponse startVerification(UUID userId, UidaiStartRequest request) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        if (user.getAccountStatus() != AccountStatus.ACTIVE) {
            throw new AccountInactiveException("Inactive accounts cannot initiate identity verification");
        }

        if (user.getVerificationState() == VerificationState.VERIFIED) {
            return UidaiStartResponse.builder()
                    .status("ALREADY_VERIFIED")
                    .message("User identity is already verified for marketplace participation.")
                    .build();
        }

        UidaiVerificationProvider.UidaiInitiationResult result =
                verificationProvider.initiate(request.getAadhaarNumber(), request.isConsent());

        if (!result.isInitiated()) {
            throw new ApiException(result.getMessage(), HttpStatus.BAD_REQUEST);
        }

        UidaiVerificationRecord record = UidaiVerificationRecord.builder()
                .userId(userId)
                .transactionId(result.getTransactionId())
                .maskedAadhaarHash(result.getMaskedReferenceHash())
                .status("PENDING")
                .build();
        recordRepository.save(record);

        user.setVerificationState(VerificationState.PENDING);
        userRepository.save(user);

        return UidaiStartResponse.builder()
                .transactionId(result.getTransactionId())
                .status("PENDING")
                .message(result.getMessage())
                .build();
    }

    @Transactional
    public VerificationStatusResponse verifyOtp(UUID userId, UidaiVerifyOtpRequest request) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        if (user.getAccountStatus() != AccountStatus.ACTIVE) {
            throw new AccountInactiveException("Inactive accounts cannot complete verification");
        }

        UidaiVerificationRecord record = recordRepository.findByTransactionId(request.getTransactionId())
                .orElseThrow(() -> new ResourceNotFoundException("Verification transaction not found"));

        if (!record.getUserId().equals(userId)) {
            throw new ApiException("Transaction does not belong to the authenticated user", HttpStatus.FORBIDDEN);
        }

        UidaiVerificationProvider.UidaiValidationResult validationResult =
                verificationProvider.validateOtp(request.getTransactionId(), request.getOtp());

        if (validationResult.isSuccess()) {
            record.setStatus("COMPLETED");
            record.setCompletedAt(Instant.now());
            recordRepository.save(record);

            user.setVerificationState(VerificationState.VERIFIED);
            userRepository.save(user);

            log.info("User {} successfully verified with UIDAI", userId);

            return VerificationStatusResponse.builder()
                    .userId(userId)
                    .verificationState(VerificationState.VERIFIED)
                    .verified(true)
                    .message("Identity verification successful. Marketplace access is now unlocked.")
                    .completedAt(record.getCompletedAt())
                    .build();
        } else {
            record.setStatus("FAILED");
            record.setCompletedAt(Instant.now());
            recordRepository.save(record);

            user.setVerificationState(VerificationState.REJECTED);
            userRepository.save(user);

            log.warn("UIDAI verification failed for user {}", userId);

            return VerificationStatusResponse.builder()
                    .userId(userId)
                    .verificationState(VerificationState.REJECTED)
                    .verified(false)
                    .message(validationResult.getMessage())
                    .completedAt(record.getCompletedAt())
                    .build();
        }
    }

    @Transactional(readOnly = true)
    public VerificationStatusResponse getStatus(UUID userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        return VerificationStatusResponse.builder()
                .userId(userId)
                .verificationState(user.getVerificationState())
                .verified(user.getVerificationState() == VerificationState.VERIFIED)
                .message("Current identity verification state: " + user.getVerificationState())
                .build();
    }
}
