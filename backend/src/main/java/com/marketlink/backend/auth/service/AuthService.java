package com.marketlink.backend.auth.service;

import com.marketlink.backend.auth.dto.*;
import com.marketlink.backend.common.exception.AccountInactiveException;
import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.common.exception.InvalidCredentialException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.user.entity.BuyerProfile;
import com.marketlink.backend.domain.user.entity.FarmerProfile;
import com.marketlink.backend.domain.user.entity.RefreshToken;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.AccountStatus;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.enums.VerificationState;
import com.marketlink.backend.domain.user.repository.BuyerProfileRepository;
import com.marketlink.backend.domain.user.repository.FarmerProfileRepository;
import com.marketlink.backend.domain.user.repository.RefreshTokenRepository;
import com.marketlink.backend.domain.user.repository.UserRepository;
import com.marketlink.backend.security.jwt.JwtProperties;
import com.marketlink.backend.security.jwt.JwtService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final FarmerProfileRepository farmerProfileRepository;
    private final BuyerProfileRepository buyerProfileRepository;
    private final RefreshTokenRepository refreshTokenRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final JwtProperties jwtProperties;

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        // Prevent Role Escalation (ADMIN cannot be self-assigned)
        if (request.getRole() == Role.ADMIN) {
            throw new ApiException("Public registration is only permitted for FARMER and BUYER roles", HttpStatus.BAD_REQUEST);
        }

        if (userRepository.existsByPhoneNumber(request.getPhoneNumber())) {
            throw new ApiException("Phone number already registered", HttpStatus.CONFLICT);
        }

        // Authoritative initial state: ACTIVE account, UNVERIFIED identity
        User user = User.builder()
                .phoneNumber(request.getPhoneNumber())
                .passwordHash(passwordEncoder.encode(request.getPassword()))
                .role(request.getRole())
                .verificationState(VerificationState.UNVERIFIED)
                .accountStatus(AccountStatus.ACTIVE)
                .build();

        user = userRepository.save(user);

        // Create role-specific initial profile atomically
        if (user.getRole() == Role.FARMER) {
            FarmerProfile profile = FarmerProfile.builder()
                    .userId(user.getId())
                    .fullName(request.getFullName())
                    .village(request.getVillage())
                    .district(request.getDistrict())
                    .state(request.getState())
                    .build();
            farmerProfileRepository.save(profile);
        } else if (user.getRole() == Role.BUYER) {
            BuyerProfile profile = BuyerProfile.builder()
                    .userId(user.getId())
                    .businessName(request.getFullName())
                    .gstin(request.getGstin())
                    .district(request.getDistrict())
                    .state(request.getState())
                    .build();
            buyerProfileRepository.save(profile);
        }

        String accessToken = jwtService.generateAccessToken(user);
        String refreshTokenStr = jwtService.generateRefreshToken(user);

        saveRefreshTokenRecord(user.getId(), refreshTokenStr);

        return AuthResponse.builder()
                .accessToken(accessToken)
                .refreshToken(refreshTokenStr)
                .tokenType("Bearer")
                .user(SafeUserProfileDto.fromUser(user))
                .build();
    }

    @Transactional
    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByPhoneNumber(request.getPhoneNumber())
                .orElseThrow(() -> new InvalidCredentialException("Invalid phone number or password"));

        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new InvalidCredentialException("Invalid phone number or password");
        }

        if (user.getAccountStatus() == AccountStatus.DISABLED) {
            throw new AccountInactiveException("Account is disabled. Please contact support.");
        }
        if (user.getAccountStatus() == AccountStatus.LOCKED) {
            throw new AccountInactiveException("Account is locked. Please contact support.");
        }

        String accessToken = jwtService.generateAccessToken(user);
        String refreshTokenStr = jwtService.generateRefreshToken(user);

        saveRefreshTokenRecord(user.getId(), refreshTokenStr);

        return AuthResponse.builder()
                .accessToken(accessToken)
                .refreshToken(refreshTokenStr)
                .tokenType("Bearer")
                .user(SafeUserProfileDto.fromUser(user))
                .build();
    }

    @Transactional
    public AuthResponse refreshToken(RefreshTokenRequest request) {
        String refreshTokenStr = request.getRefreshToken();
        if (!jwtService.validateToken(refreshTokenStr)) {
            throw new ApiException("Invalid or expired refresh token", HttpStatus.UNAUTHORIZED);
        }

        String tokenType = jwtService.extractTokenType(refreshTokenStr);
        if (!"REFRESH".equals(tokenType)) {
            throw new ApiException("Token is not a refresh token", HttpStatus.BAD_REQUEST);
        }

        // Validate token against persistent revocation store
        RefreshToken storedToken = refreshTokenRepository.findByToken(refreshTokenStr)
                .orElseThrow(() -> new ApiException("Refresh token has been revoked or not found", HttpStatus.UNAUTHORIZED));

        if (storedToken.isRevoked() || storedToken.getExpiryDate().isBefore(Instant.now())) {
            throw new ApiException("Refresh token has expired or was revoked", HttpStatus.UNAUTHORIZED);
        }

        String phoneNumber = jwtService.extractPhoneNumber(refreshTokenStr);
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        if (user.getAccountStatus() != AccountStatus.ACTIVE) {
            throw new AccountInactiveException("Account is not active");
        }

        // Single-use token rotation: revoke old refresh token and issue a fresh pair
        storedToken.setRevoked(true);
        refreshTokenRepository.save(storedToken);

        String newAccessToken = jwtService.generateAccessToken(user);
        String newRefreshToken = jwtService.generateRefreshToken(user);
        saveRefreshTokenRecord(user.getId(), newRefreshToken);

        return AuthResponse.builder()
                .accessToken(newAccessToken)
                .refreshToken(newRefreshToken)
                .tokenType("Bearer")
                .user(SafeUserProfileDto.fromUser(user))
                .build();
    }

    @Transactional
    public void logout(UUID userId) {
        if (userId != null) {
            refreshTokenRepository.revokeAllByUserId(userId);
            log.info("Revoked all active refresh tokens for user {}", userId);
        }
    }

    @Transactional(readOnly = true)
    public SafeUserProfileDto getCurrentUserProfile(UUID userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));
        return SafeUserProfileDto.fromUser(user);
    }

    private void saveRefreshTokenRecord(UUID userId, String tokenStr) {
        RefreshToken tokenRecord = RefreshToken.builder()
                .userId(userId)
                .token(tokenStr)
                .expiryDate(Instant.now().plusMillis(jwtProperties.getRefreshExpirationMs()))
                .revoked(false)
                .build();
        refreshTokenRepository.save(tokenRecord);
    }
}
