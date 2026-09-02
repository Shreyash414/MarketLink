package com.marketlink.backend.security.authorization;

import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.AccountStatus;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.enums.VerificationState;
import com.marketlink.backend.domain.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Optional;
import java.util.UUID;

/**
 * Centralized marketplace authorization policy.
 *
 * PROTOTYPE MODE NOTICE:
 * When 'marketlink.security.prototype-mode=true' is configured (e.g. for SIH demo),
 * marketplace authorization bypasses the UIDAI identity verification requirement.
 * In this mode, authorization requires:
 *   - Authenticated user
 *   - ACTIVE account status
 *   - Correct role (FARMER / BUYER)
 *   - Resource ownership where applicable
 *
 * In PRODUCTION MODE ('marketlink.security.prototype-mode=false'), authorization strictly requires:
 *   - Authenticated user
 *   - ACTIVE account status
 *   - Correct role
 *   - VerificationState == VERIFIED
 *   - Resource ownership where applicable
 */
@Slf4j
@Component("marketplaceAuth")
@RequiredArgsConstructor
public class MarketplaceAuthorizationPolicy {

    private final UserRepository userRepository;
    private final LotRepository lotRepository;

    @Value("${marketlink.security.prototype-mode:false}")
    private boolean prototypeMode;

    public boolean isPrototypeMode() {
        return prototypeMode;
    }

    public void setPrototypeMode(boolean prototypeMode) {
        this.prototypeMode = prototypeMode;
    }

    /**
     * Server-side check for FARMER marketplace operations (create/publish/manage lots).
     */
    public boolean isVerifiedFarmer(UUID userId) {
        if (userId == null) {
            return false;
        }
        Optional<User> userOpt = userRepository.findById(userId);
        if (userOpt.isEmpty()) {
            return false;
        }
        User user = userOpt.get();

        boolean roleAndStatusOk = user.getAccountStatus() == AccountStatus.ACTIVE
                && user.getRole() == Role.FARMER;

        if (!roleAndStatusOk) {
            log.warn("Farmer marketplace access denied for user {}: status={}, role={}",
                    userId, user.getAccountStatus(), user.getRole());
            return false;
        }

        // In prototype mode, unverified farmers are granted marketplace access
        if (prototypeMode) {
            return true;
        }

        // In production mode, verificationState must strictly be VERIFIED
        boolean verified = user.getVerificationState() == VerificationState.VERIFIED;
        if (!verified) {
            log.warn("Farmer marketplace access denied for user {}: verificationState={}",
                    userId, user.getVerificationState());
        }
        return verified;
    }

    /**
     * Server-side check for BUYER marketplace operations (create bids/offers).
     */
    public boolean isVerifiedBuyer(UUID userId) {
        if (userId == null) {
            return false;
        }
        Optional<User> userOpt = userRepository.findById(userId);
        if (userOpt.isEmpty()) {
            return false;
        }
        User user = userOpt.get();

        boolean roleAndStatusOk = user.getAccountStatus() == AccountStatus.ACTIVE
                && user.getRole() == Role.BUYER;

        if (!roleAndStatusOk) {
            log.warn("Buyer marketplace access denied for user {}: status={}, role={}",
                    userId, user.getAccountStatus(), user.getRole());
            return false;
        }

        // In prototype mode, unverified buyers are granted marketplace access
        if (prototypeMode) {
            return true;
        }

        // In production mode, verificationState must strictly be VERIFIED
        boolean verified = user.getVerificationState() == VerificationState.VERIFIED;
        if (!verified) {
            log.warn("Buyer marketplace access denied for user {}: verificationState={}",
                    userId, user.getVerificationState());
        }
        return verified;
    }

    /**
     * Server-side check for general marketplace browsing.
     */
    public boolean isVerifiedParticipant(UUID userId) {
        if (userId == null) {
            return false;
        }
        Optional<User> userOpt = userRepository.findById(userId);
        if (userOpt.isEmpty()) {
            return false;
        }
        User user = userOpt.get();

        boolean roleAndStatusOk = user.getAccountStatus() == AccountStatus.ACTIVE
                && (user.getRole() == Role.FARMER || user.getRole() == Role.BUYER);

        if (!roleAndStatusOk) {
            return false;
        }

        if (prototypeMode) {
            return true;
        }

        return user.getVerificationState() == VerificationState.VERIFIED;
    }

    /**
     * Checks if the authenticated farmer owns the given lot.
     */
    public boolean isLotOwner(UUID userId, UUID lotId) {
        if (userId == null || lotId == null) {
            return false;
        }
        return lotRepository.findById(lotId)
                .map(lot -> lot.getFarmerId().equals(userId))
                .orElse(false);
    }
}
