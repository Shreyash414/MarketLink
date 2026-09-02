package com.marketlink.backend.auth.controller;

import com.marketlink.backend.auth.dto.*;
import com.marketlink.backend.auth.service.AuthService;
import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.security.principal.UserPrincipal;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/register")
    public ResponseEntity<ApiResponse<AuthResponse>> register(@Valid @RequestBody RegisterRequest request) {
        AuthResponse response = authService.register(request);
        return new ResponseEntity<>(ApiResponse.success("Account registered successfully as basic user", response), HttpStatus.CREATED);
    }

    @PostMapping("/login")
    public ResponseEntity<ApiResponse<AuthResponse>> login(@Valid @RequestBody LoginRequest request) {
        AuthResponse response = authService.login(request);
        return ResponseEntity.ok(ApiResponse.success("Login successful", response));
    }

    @PostMapping("/refresh")
    public ResponseEntity<ApiResponse<AuthResponse>> refreshToken(@Valid @RequestBody RefreshTokenRequest request) {
        AuthResponse response = authService.refreshToken(request);
        return ResponseEntity.ok(ApiResponse.success("Token refreshed successfully", response));
    }

    @PostMapping("/logout")
    public ResponseEntity<ApiResponse<String>> logout(@AuthenticationPrincipal UserPrincipal principal) {
        if (principal != null) {
            authService.logout(principal.getId());
        }
        return ResponseEntity.ok(ApiResponse.success("Logged out successfully", "Active refresh tokens invalidated"));
    }

    @GetMapping("/me")
    public ResponseEntity<ApiResponse<SafeUserProfileDto>> getCurrentUser(@AuthenticationPrincipal UserPrincipal principal) {
        SafeUserProfileDto profile = authService.getCurrentUserProfile(principal.getId());
        return ResponseEntity.ok(ApiResponse.success(profile));
    }
}
