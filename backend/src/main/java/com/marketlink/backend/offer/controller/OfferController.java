package com.marketlink.backend.offer.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.offer.dto.CreateOfferRequest;
import com.marketlink.backend.offer.dto.OfferResponse;
import com.marketlink.backend.offer.service.OfferService;
import com.marketlink.backend.security.principal.UserPrincipal;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
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
@RequiredArgsConstructor
@Tag(name = "Buyer Offers", description = "Produce lot purchase offers, counter-negotiations, and safe offer acceptance APIs")
public class OfferController {

    private final OfferService offerService;

    @PostMapping("/api/v1/lots/{lotId}/offers")
    @PreAuthorize("@marketplaceAuth.isVerifiedBuyer(principal.id)")
    @Operation(summary = "Place purchase offer", description = "Verified buyer submits a price offer for an active published lot",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "201",
                    description = "Offer placed successfully",
                    content = @Content(schema = @Schema(implementation = OfferResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "Lot not published, offered price below minimum, or quantity exceeds lot"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: User is not a verified buyer"
            )
    })
    public ResponseEntity<ApiResponse<OfferResponse>> createOffer(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the lot")
            @PathVariable UUID lotId,
            @Valid @RequestBody CreateOfferRequest request) {
        OfferResponse response = offerService.createOffer(principal.getId(), lotId, request);
        return new ResponseEntity<>(ApiResponse.success("Offer placed successfully", response), HttpStatus.CREATED);
    }

    @GetMapping("/api/v1/lots/{lotId}/offers")
    @Operation(summary = "Get offers for a lot", description = "Farmer retrieves all offers on their lot, or a buyer views their own offers on the lot",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Offers retrieved successfully",
                    content = @Content(array = @ArraySchema(schema = @Schema(implementation = OfferResponse.class)))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Lot not found"
            )
    })
    public ResponseEntity<ApiResponse<List<OfferResponse>>> getOffersForLot(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the lot")
            @PathVariable UUID lotId) {
        List<OfferResponse> offers = offerService.getOffersForLot(principal.getId(), lotId);
        return ResponseEntity.ok(ApiResponse.success(offers));
    }

    @GetMapping("/api/v1/buyers/me/offers")
    @PreAuthorize("@marketplaceAuth.isVerifiedBuyer(principal.id)")
    @Operation(summary = "Get my buyer offers", description = "Buyer retrieves all offers they have placed across all produce lots",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Buyer offers retrieved successfully",
                    content = @Content(array = @ArraySchema(schema = @Schema(implementation = OfferResponse.class)))
            )
    })
    public ResponseEntity<ApiResponse<List<OfferResponse>>> getMyOffers(
            @AuthenticationPrincipal UserPrincipal principal) {
        List<OfferResponse> offers = offerService.getOffersByBuyer(principal.getId());
        return ResponseEntity.ok(ApiResponse.success(offers));
    }

    @GetMapping("/api/v1/offers/{id}")
    @Operation(summary = "Get offer details by ID", description = "Retrieves details of a specific offer",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Offer retrieved successfully",
                    content = @Content(schema = @Schema(implementation = OfferResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller is neither the lot owner nor the offer creator"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Offer not found"
            )
    })
    public ResponseEntity<ApiResponse<OfferResponse>> getOfferById(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the offer")
            @PathVariable UUID id) {
        OfferResponse response = offerService.getOfferById(principal.getId(), id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PostMapping("/api/v1/offers/{id}/accept")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id)")
    @Operation(summary = "Accept purchase offer", description = "Farmer accepts a pending offer. Transitions the offer and lot to ACCEPTED and auto-rejects other pending offers.",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Offer accepted successfully",
                    content = @Content(schema = @Schema(implementation = OfferResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "Offer is not in PENDING state or lot is not in active status"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller does not own this lot"
            )
    })
    public ResponseEntity<ApiResponse<OfferResponse>> acceptOffer(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the offer to accept")
            @PathVariable UUID id) {
        OfferResponse response = offerService.acceptOffer(principal.getId(), id);
        return ResponseEntity.ok(ApiResponse.success("Offer accepted successfully", response));
    }

    @PostMapping("/api/v1/offers/{id}/reject")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id)")
    @Operation(summary = "Reject purchase offer", description = "Farmer rejects a pending offer",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Offer rejected successfully",
                    content = @Content(schema = @Schema(implementation = OfferResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller does not own this lot"
            )
    })
    public ResponseEntity<ApiResponse<OfferResponse>> rejectOffer(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the offer to reject")
            @PathVariable UUID id) {
        OfferResponse response = offerService.rejectOffer(principal.getId(), id);
        return ResponseEntity.ok(ApiResponse.success("Offer rejected successfully", response));
    }

    @PostMapping("/api/v1/offers/{id}/cancel")
    @PreAuthorize("@marketplaceAuth.isVerifiedBuyer(principal.id)")
    @Operation(summary = "Cancel purchase offer", description = "Buyer cancels their own pending offer",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Offer cancelled successfully",
                    content = @Content(schema = @Schema(implementation = OfferResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller is not the buyer who placed this offer"
            )
    })
    public ResponseEntity<ApiResponse<OfferResponse>> cancelOffer(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the offer to cancel")
            @PathVariable UUID id) {
        OfferResponse response = offerService.cancelOffer(principal.getId(), id);
        return ResponseEntity.ok(ApiResponse.success("Offer cancelled successfully", response));
    }
}
