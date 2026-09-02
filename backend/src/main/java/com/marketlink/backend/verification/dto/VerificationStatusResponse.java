package com.marketlink.backend.verification.dto;

import com.marketlink.backend.domain.user.enums.VerificationState;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class VerificationStatusResponse {
    private UUID userId;
    private VerificationState verificationState;
    private boolean verified;
    private String message;
    private Instant completedAt;
}
