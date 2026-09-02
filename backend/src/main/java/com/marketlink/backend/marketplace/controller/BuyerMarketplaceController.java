package com.marketlink.backend.marketplace.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.marketplace.dto.BidResponseDto;
import com.marketlink.backend.marketplace.dto.CreateBidRequest;
import com.marketlink.backend.marketplace.service.MarketplaceBidService;
import com.marketlink.backend.security.principal.UserPrincipal;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/marketplace/bids")
@RequiredArgsConstructor
public class BuyerMarketplaceController {

    private final MarketplaceBidService bidService;

    @PostMapping
    @PreAuthorize("@marketplaceAuth.isVerifiedBuyer(principal.id)")
    public ResponseEntity<ApiResponse<BidResponseDto>> createBid(
            @AuthenticationPrincipal UserPrincipal principal,
            @Valid @RequestBody CreateBidRequest request) {
        BidResponseDto bid = bidService.createBid(principal.getId(), request);
        return new ResponseEntity<>(ApiResponse.success("Bid placed successfully", bid), HttpStatus.CREATED);
    }

    @GetMapping("/my")
    @PreAuthorize("@marketplaceAuth.isVerifiedBuyer(principal.id)")
    public ResponseEntity<ApiResponse<List<BidResponseDto>>> getMyBids(
            @AuthenticationPrincipal UserPrincipal principal) {
        List<BidResponseDto> bids = bidService.getBuyerBids(principal.getId());
        return ResponseEntity.ok(ApiResponse.success(bids));
    }
}
