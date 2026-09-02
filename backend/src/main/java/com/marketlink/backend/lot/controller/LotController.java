package com.marketlink.backend.lot.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.lot.dto.CreateLotRequest;
import com.marketlink.backend.lot.dto.LotResponse;
import com.marketlink.backend.lot.dto.UpdateLotRequest;
import com.marketlink.backend.lot.service.LotService;
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
@RequestMapping("/api/v1")
@RequiredArgsConstructor
@Tag(name = "Lots", description = "Farmer produce listing and lot lifecycle management APIs")
public class LotController {

    private final LotService lotService;

    @PostMapping("/lots")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id)")
    @Operation(summary = "Create lot", description = "Farmer creates a new produce lot in DRAFT status",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "201",
                    description = "Lot created successfully in DRAFT status",
                    content = @Content(schema = @Schema(implementation = LotResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "Invalid payload or validation failed"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller is not a verified farmer"
            )
    })
    public ResponseEntity<ApiResponse<LotResponse>> createLot(
            @AuthenticationPrincipal UserPrincipal principal,
            @Valid @RequestBody CreateLotRequest request) {
        LotResponse response = lotService.createLot(principal.getId(), request);
        return new ResponseEntity<>(ApiResponse.success("Lot created successfully", response), HttpStatus.CREATED);
    }

    @GetMapping("/lots")
    @Operation(summary = "Browse published lots", description = "Retrieves active marketplace lots with optional crop, market, and price filtering")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Published lots retrieved successfully",
                    content = @Content(array = @ArraySchema(schema = @Schema(implementation = LotResponse.class)))
            )
    })
    public ResponseEntity<ApiResponse<List<LotResponse>>> getPublishedLots(
            @Parameter(description = "Filter by crop UUID")
            @RequestParam(required = false) UUID cropId,
            @Parameter(description = "Filter by market UUID")
            @RequestParam(required = false) UUID marketId,
            @Parameter(description = "Minimum expected price")
            @RequestParam(required = false) Double minPrice,
            @Parameter(description = "Maximum expected price")
            @RequestParam(required = false) Double maxPrice) {
        List<LotResponse> lots = lotService.getPublishedLots(cropId, marketId, minPrice, maxPrice);
        return ResponseEntity.ok(ApiResponse.success(lots));
    }

    @GetMapping("/lots/{id}")
    @Operation(summary = "Get lot by ID", description = "Retrieves details of a specific produce lot by UUID")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Lot details retrieved successfully",
                    content = @Content(schema = @Schema(implementation = LotResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Lot not found"
            )
    })
    public ResponseEntity<ApiResponse<LotResponse>> getLotById(
            @Parameter(description = "Unique UUID of the lot")
            @PathVariable UUID id) {
        LotResponse lot = lotService.getLotById(id);
        return ResponseEntity.ok(ApiResponse.success(lot));
    }

    @GetMapping("/farmers/me/lots")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id)")
    @Operation(summary = "Get my lots", description = "Authenticated farmer retrieves all lots they own",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Farmer's lots retrieved successfully",
                    content = @Content(array = @ArraySchema(schema = @Schema(implementation = LotResponse.class)))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller is not a verified farmer"
            )
    })
    public ResponseEntity<ApiResponse<List<LotResponse>>> getMyLots(
            @AuthenticationPrincipal UserPrincipal principal) {
        List<LotResponse> lots = lotService.getFarmerLots(principal.getId());
        return ResponseEntity.ok(ApiResponse.success(lots));
    }

    @PutMapping("/lots/{id}")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id) and @marketplaceAuth.isLotOwner(principal.id, #id)")
    @Operation(summary = "Update draft lot", description = "Farmer updates properties of a draft lot",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Draft lot updated successfully",
                    content = @Content(schema = @Schema(implementation = LotResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "Invalid payload or lot is not in DRAFT status"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller does not own this lot"
            )
    })
    public ResponseEntity<ApiResponse<LotResponse>> updateLot(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the draft lot to update")
            @PathVariable UUID id,
            @Valid @RequestBody UpdateLotRequest request) {
        LotResponse updated = lotService.updateLot(principal.getId(), id, request);
        return ResponseEntity.ok(ApiResponse.success("Lot updated successfully", updated));
    }

    @PostMapping("/lots/{id}/publish")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id) and @marketplaceAuth.isLotOwner(principal.id, #id)")
    @Operation(summary = "Publish lot", description = "Farmer publishes a draft or quality-verified lot to the marketplace",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Lot published to marketplace successfully",
                    content = @Content(schema = @Schema(implementation = LotResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "Lot is not in a publishable status"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller does not own this lot"
            )
    })
    public ResponseEntity<ApiResponse<LotResponse>> publishLot(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the lot to publish")
            @PathVariable UUID id) {
        LotResponse published = lotService.publishLot(principal.getId(), id);
        return ResponseEntity.ok(ApiResponse.success("Lot published successfully to marketplace", published));
    }

    @PostMapping("/lots/{id}/close")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id) and @marketplaceAuth.isLotOwner(principal.id, #id)")
    @Operation(summary = "Close lot", description = "Farmer marks a lot as CLOSED",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Lot closed successfully",
                    content = @Content(schema = @Schema(implementation = LotResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller does not own this lot"
            )
    })
    public ResponseEntity<ApiResponse<LotResponse>> closeLot(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the lot to close")
            @PathVariable UUID id) {
        LotResponse closed = lotService.closeLot(principal.getId(), id);
        return ResponseEntity.ok(ApiResponse.success("Lot closed successfully", closed));
    }

    @PostMapping("/lots/{id}/cancel")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id) and @marketplaceAuth.isLotOwner(principal.id, #id)")
    @Operation(summary = "Cancel lot", description = "Farmer cancels an active or draft lot",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Lot cancelled successfully",
                    content = @Content(schema = @Schema(implementation = LotResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "Lot cannot be cancelled in current status"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller does not own this lot"
            )
    })
    public ResponseEntity<ApiResponse<LotResponse>> cancelLot(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the lot to cancel")
            @PathVariable UUID id) {
        LotResponse cancelled = lotService.cancelLot(principal.getId(), id);
        return ResponseEntity.ok(ApiResponse.success("Lot cancelled successfully", cancelled));
    }
}
