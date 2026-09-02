package com.marketlink.backend.profile.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.profile.dto.BuyerProfileDto;
import com.marketlink.backend.profile.dto.UpdateBuyerProfileRequest;
import com.marketlink.backend.profile.service.ProfileService;
import com.marketlink.backend.security.principal.UserPrincipal;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/buyers")
@RequiredArgsConstructor
@PreAuthorize("hasRole('BUYER')")
public class BuyerProfileController {

    private final ProfileService profileService;

    @GetMapping("/me")
    public ResponseEntity<ApiResponse<BuyerProfileDto>> getMyProfile(@AuthenticationPrincipal UserPrincipal principal) {
        BuyerProfileDto profile = profileService.getBuyerProfile(principal.getId());
        return ResponseEntity.ok(ApiResponse.success(profile));
    }

    @PutMapping("/me")
    public ResponseEntity<ApiResponse<BuyerProfileDto>> updateMyProfile(
            @AuthenticationPrincipal UserPrincipal principal,
            @RequestBody UpdateBuyerProfileRequest request) {
        BuyerProfileDto profile = profileService.updateBuyerProfile(principal.getId(), request);
        return ResponseEntity.ok(ApiResponse.success("Profile updated successfully", profile));
    }
}
