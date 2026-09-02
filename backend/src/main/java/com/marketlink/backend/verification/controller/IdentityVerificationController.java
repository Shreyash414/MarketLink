package com.marketlink.backend.verification.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.security.principal.UserPrincipal;
import com.marketlink.backend.verification.dto.UidaiStartRequest;
import com.marketlink.backend.verification.dto.UidaiStartResponse;
import com.marketlink.backend.verification.dto.UidaiVerifyOtpRequest;
import com.marketlink.backend.verification.dto.VerificationStatusResponse;
import com.marketlink.backend.verification.service.IdentityVerificationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/verification")
@RequiredArgsConstructor
public class IdentityVerificationController {

    private final IdentityVerificationService verificationService;

    @PostMapping("/uidai/start")
    public ResponseEntity<ApiResponse<UidaiStartResponse>> startVerification(
            @AuthenticationPrincipal UserPrincipal principal,
            @Valid @RequestBody UidaiStartRequest request) {
        UidaiStartResponse response = verificationService.startVerification(principal.getId(), request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PostMapping("/uidai/verify-otp")
    public ResponseEntity<ApiResponse<VerificationStatusResponse>> verifyOtp(
            @AuthenticationPrincipal UserPrincipal principal,
            @Valid @RequestBody UidaiVerifyOtpRequest request) {
        VerificationStatusResponse response = verificationService.verifyOtp(principal.getId(), request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/status")
    public ResponseEntity<ApiResponse<VerificationStatusResponse>> getStatus(
            @AuthenticationPrincipal UserPrincipal principal) {
        VerificationStatusResponse response = verificationService.getStatus(principal.getId());
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
