package com.marketlink.backend.voice.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.security.principal.UserPrincipal;
import com.marketlink.backend.voice.dto.VoiceOfferResponse;
import com.marketlink.backend.voice.dto.VoicePriceQueryResponse;
import com.marketlink.backend.voice.service.VoiceChannelService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/voice")
@RequiredArgsConstructor
@Tag(name = "Voice & Feature Phone", description = "Voice/IVR price queries and offer acceptance APIs restricted to lightweight voice interaction")
public class VoiceChannelController {

    private final VoiceChannelService voiceChannelService;

    @GetMapping("/prices")
    @Operation(summary = "Voice price query", description = "IVR/voice assistant query returning text-to-speech synthesized summary of mandi prices")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Voice price response retrieved successfully",
                    content = @Content(schema = @Schema(implementation = VoicePriceQueryResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Crop or price data not found"
            )
    })
    public ResponseEntity<ApiResponse<VoicePriceQueryResponse>> queryPrice(
            @Parameter(description = "Crop name spoken by user (e.g. Onion, Tomato)", required = true)
            @RequestParam String cropName,
            @Parameter(description = "Optional market name spoken by user (e.g. Pune APMC)")
            @RequestParam(required = false) String marketName) {
        VoicePriceQueryResponse response = voiceChannelService.queryVoicePrice(cropName, marketName);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/offers")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id)")
    @Operation(summary = "Voice pending offers inquiry", description = "Retrieves pending offers formatted for voice menu playback to the calling farmer",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Pending voice offers retrieved successfully",
                    content = @Content(array = @ArraySchema(schema = @Schema(implementation = VoiceOfferResponse.class)))
            )
    })
    public ResponseEntity<ApiResponse<List<VoiceOfferResponse>>> getPendingOffers(
            @AuthenticationPrincipal UserPrincipal principal) {
        List<VoiceOfferResponse> offers = voiceChannelService.getPendingOffersForFarmer(principal.getId());
        return ResponseEntity.ok(ApiResponse.success(offers));
    }

    @PostMapping("/offers/{id}/accept")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id)")
    @Operation(summary = "Voice offer acceptance", description = "Farmer confirms acceptance of an offer via voice/DTMF prompt",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Offer accepted via voice"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller is not the lot owner"
            )
    })
    public ResponseEntity<ApiResponse<String>> acceptOffer(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the offer")
            @PathVariable UUID id) {
        String message = voiceChannelService.acceptOfferByVoice(principal.getId(), id);
        return ResponseEntity.ok(ApiResponse.success(message, message));
    }
}
