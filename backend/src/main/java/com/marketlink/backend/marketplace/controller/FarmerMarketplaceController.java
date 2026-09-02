package com.marketlink.backend.marketplace.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.marketplace.dto.AcceptBidRequest;
import com.marketlink.backend.marketplace.dto.CreateLotRequest;
import com.marketlink.backend.marketplace.dto.LotResponseDto;
import com.marketlink.backend.marketplace.service.MarketplaceLotService;
import com.marketlink.backend.security.principal.UserPrincipal;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/marketplace/lots")
@RequiredArgsConstructor
public class FarmerMarketplaceController {

    private final MarketplaceLotService lotService;

    @PostMapping
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id)")
    public ResponseEntity<ApiResponse<LotResponseDto>> createLot(
            @AuthenticationPrincipal UserPrincipal principal,
            @Valid @RequestBody CreateLotRequest request) {
        LotResponseDto lot = lotService.createLot(principal.getId(), request);
        return new ResponseEntity<>(ApiResponse.success("Lot created successfully", lot), HttpStatus.CREATED);
    }

    @PutMapping("/{id}/publish")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id) and @marketplaceAuth.isLotOwner(principal.id, #id)")
    public ResponseEntity<ApiResponse<LotResponseDto>> publishLot(
            @AuthenticationPrincipal UserPrincipal principal,
            @PathVariable UUID id) {
        LotResponseDto lot = lotService.publishLot(principal.getId(), id);
        return ResponseEntity.ok(ApiResponse.success("Lot published successfully to marketplace", lot));
    }

    @PostMapping("/{id}/accept-bid")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id) and @marketplaceAuth.isLotOwner(principal.id, #id)")
    public ResponseEntity<ApiResponse<LotResponseDto>> acceptBid(
            @AuthenticationPrincipal UserPrincipal principal,
            @PathVariable UUID id,
            @Valid @RequestBody AcceptBidRequest request) {
        LotResponseDto lot = lotService.acceptBid(principal.getId(), id, request);
        return ResponseEntity.ok(ApiResponse.success("Bid accepted and lot sold", lot));
    }

    @GetMapping("/my")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id)")
    public ResponseEntity<ApiResponse<List<LotResponseDto>>> getMyLots(
            @AuthenticationPrincipal UserPrincipal principal) {
        List<LotResponseDto> lots = lotService.getFarmerLots(principal.getId());
        return ResponseEntity.ok(ApiResponse.success(lots));
    }
}
