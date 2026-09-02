package com.marketlink.backend.marketplace.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.marketplace.dto.LotResponseDto;
import com.marketlink.backend.marketplace.service.MarketplaceLotService;
import com.marketlink.backend.security.principal.UserPrincipal;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/marketplace/browse")
@RequiredArgsConstructor
public class MarketplaceBrowsingController {

    private final MarketplaceLotService lotService;

    @GetMapping("/lots")
    @PreAuthorize("@marketplaceAuth.isVerifiedParticipant(principal.id)")
    public ResponseEntity<ApiResponse<List<LotResponseDto>>> getPublishedLots(
            @AuthenticationPrincipal UserPrincipal principal) {
        List<LotResponseDto> lots = lotService.getPublishedLots();
        return ResponseEntity.ok(ApiResponse.success(lots));
    }

    @GetMapping("/lots/{id}")
    @PreAuthorize("@marketplaceAuth.isVerifiedParticipant(principal.id)")
    public ResponseEntity<ApiResponse<LotResponseDto>> getLot(
            @AuthenticationPrincipal UserPrincipal principal,
            @PathVariable UUID id) {
        LotResponseDto lot = lotService.getLotById(id);
        return ResponseEntity.ok(ApiResponse.success(lot));
    }
}
