package com.marketlink.backend.market.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.market.dto.CreateMarketRequest;
import com.marketlink.backend.market.dto.MarketResponse;
import com.marketlink.backend.market.dto.UpdateMarketRequest;
import com.marketlink.backend.market.service.MarketService;
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
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/markets")
@RequiredArgsConstructor
@Tag(name = "Markets", description = "APMC / Mandi market location APIs for geographic produce discovery and pricing")
public class MarketController {

    private final MarketService marketService;

    @GetMapping
    @Operation(summary = "Get all markets", description = "Retrieves markets with optional filtering by state, district, and active status")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Markets retrieved successfully",
                    content = @Content(array = @ArraySchema(schema = @Schema(implementation = MarketResponse.class)))
            )
    })
    public ResponseEntity<ApiResponse<List<MarketResponse>>> getAllMarkets(
            @Parameter(description = "Filter by state (e.g., Maharashtra)")
            @RequestParam(required = false) String state,
            @Parameter(description = "Filter by district (e.g., Pune)")
            @RequestParam(required = false) String district,
            @Parameter(description = "Filter only active markets (defaults to true)")
            @RequestParam(required = false, defaultValue = "true") Boolean activeOnly) {
        List<MarketResponse> markets = marketService.getAllMarkets(state, district, activeOnly);
        return ResponseEntity.ok(ApiResponse.success(markets));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get market by ID", description = "Retrieves details of a specific market by its UUID")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Market retrieved successfully",
                    content = @Content(schema = @Schema(implementation = MarketResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Market not found with provided UUID"
            )
    })
    public ResponseEntity<ApiResponse<MarketResponse>> getMarketById(
            @Parameter(description = "Unique UUID of the market")
            @PathVariable UUID id) {
        MarketResponse market = marketService.getMarketById(id);
        return ResponseEntity.ok(ApiResponse.success(market));
    }

    @PostMapping
    @Operation(summary = "Create market", description = "Registers a new APMC / Mandi market in the system",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "201",
                    description = "Market created successfully",
                    content = @Content(schema = @Schema(implementation = MarketResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "Invalid payload or validation failed"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "409",
                    description = "Market already exists in this district and state"
            )
    })
    public ResponseEntity<ApiResponse<MarketResponse>> createMarket(
            @Valid @RequestBody CreateMarketRequest request) {
        MarketResponse created = marketService.createMarket(request);
        return new ResponseEntity<>(ApiResponse.success("Market created successfully", created), HttpStatus.CREATED);
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update market", description = "Updates details, coordinates, or active status of an existing market",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Market updated successfully",
                    content = @Content(schema = @Schema(implementation = MarketResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Market not found"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "409",
                    description = "Updated market details conflict with an existing market in same region"
            )
    })
    public ResponseEntity<ApiResponse<MarketResponse>> updateMarket(
            @Parameter(description = "Unique UUID of the market to update")
            @PathVariable UUID id,
            @Valid @RequestBody UpdateMarketRequest request) {
        MarketResponse updated = marketService.updateMarket(id, request);
        return ResponseEntity.ok(ApiResponse.success("Market updated successfully", updated));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete market", description = "Removes a market location record",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Market deleted successfully"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Market not found"
            )
    })
    public ResponseEntity<ApiResponse<Void>> deleteMarket(
            @Parameter(description = "Unique UUID of the market to delete")
            @PathVariable UUID id) {
        marketService.deleteMarket(id);
        return ResponseEntity.ok(ApiResponse.success("Market deleted successfully", null));
    }
}
