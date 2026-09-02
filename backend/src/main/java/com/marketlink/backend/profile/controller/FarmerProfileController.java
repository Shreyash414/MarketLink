package com.marketlink.backend.profile.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.profile.dto.FarmerProfileDto;
import com.marketlink.backend.profile.dto.UpdateFarmerProfileRequest;
import com.marketlink.backend.profile.service.ProfileService;
import com.marketlink.backend.security.principal.UserPrincipal;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/farmers")
@RequiredArgsConstructor
@PreAuthorize("hasRole('FARMER')")
public class FarmerProfileController {

    private final ProfileService profileService;

    @GetMapping("/me")
    public ResponseEntity<ApiResponse<FarmerProfileDto>> getMyProfile(@AuthenticationPrincipal UserPrincipal principal) {
        FarmerProfileDto profile = profileService.getFarmerProfile(principal.getId());
        return ResponseEntity.ok(ApiResponse.success(profile));
    }

    @PutMapping("/me")
    public ResponseEntity<ApiResponse<FarmerProfileDto>> updateMyProfile(
            @AuthenticationPrincipal UserPrincipal principal,
            @RequestBody UpdateFarmerProfileRequest request) {
        FarmerProfileDto profile = profileService.updateFarmerProfile(principal.getId(), request);
        return ResponseEntity.ok(ApiResponse.success("Profile updated successfully", profile));
    }
}
