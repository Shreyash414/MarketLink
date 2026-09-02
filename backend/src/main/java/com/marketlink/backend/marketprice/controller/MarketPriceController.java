package com.marketlink.backend.marketprice.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.marketprice.dto.MarketPriceResponse;
import com.marketlink.backend.marketprice.dto.RecordMarketPriceRequest;
import com.marketlink.backend.marketprice.service.MarketPriceService;
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
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/market-prices")
@RequiredArgsConstructor
@Tag(name = "Market Prices", description = "Historical and current mandi market price observation APIs for price discovery")
public class MarketPriceController {

    private final MarketPriceService marketPriceService;

    @GetMapping
    @Operation(summary = "Query market prices", description = "Retrieves market price observations with flexible filtering by crop, market, district, state, and date range")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Market prices retrieved successfully",
                    content = @Content(array = @ArraySchema(schema = @Schema(implementation = MarketPriceResponse.class)))
            )
    })
    public ResponseEntity<ApiResponse<List<MarketPriceResponse>>> queryMarketPrices(
            @Parameter(description = "Filter by Crop UUID")
            @RequestParam(required = false) UUID cropId,
            @Parameter(description = "Filter by Market UUID")
            @RequestParam(required = false) UUID marketId,
            @Parameter(description = "Filter by State name")
            @RequestParam(required = false) String state,
            @Parameter(description = "Filter by District name")
            @RequestParam(required = false) String district,
            @Parameter(description = "Start date (YYYY-MM-DD)")
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @Parameter(description = "End date (YYYY-MM-DD)")
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {
        List<MarketPriceResponse> prices = marketPriceService.queryMarketPrices(cropId, marketId, state, district, startDate, endDate);
        return ResponseEntity.ok(ApiResponse.success(prices));
    }

    @GetMapping("/latest")
    @Operation(summary = "Get latest market price", description = "Retrieves the most recent price observation for a crop in a given market or across markets")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Latest price retrieved successfully",
                    content = @Content(schema = @Schema(implementation = MarketPriceResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "No price observations found"
            )
    })
    public ResponseEntity<ApiResponse<MarketPriceResponse>> getLatestMarketPrice(
            @Parameter(description = "Crop UUID", required = true)
            @RequestParam UUID cropId,
            @Parameter(description = "Market UUID (optional)")
            @RequestParam(required = false) UUID marketId) {
        MarketPriceResponse response = marketPriceService.getLatestMarketPrice(cropId, marketId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get price observation by ID", description = "Retrieves a single market price record by its UUID")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Price observation retrieved successfully",
                    content = @Content(schema = @Schema(implementation = MarketPriceResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Price observation not found"
            )
    })
    public ResponseEntity<ApiResponse<MarketPriceResponse>> getMarketPriceById(
            @Parameter(description = "UUID of the price record")
            @PathVariable UUID id) {
        MarketPriceResponse response = marketPriceService.getMarketPriceById(id);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PostMapping
    @Operation(summary = "Record market price", description = "Records a new market price observation and arrival quantity",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "201",
                    description = "Price record saved successfully",
                    content = @Content(schema = @Schema(implementation = MarketPriceResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "Invalid payload or price logic error (e.g. min > max)"
            )
    })
    public ResponseEntity<ApiResponse<MarketPriceResponse>> recordMarketPrice(
            @Valid @RequestBody RecordMarketPriceRequest request) {
        MarketPriceResponse created = marketPriceService.recordMarketPrice(request);
        return new ResponseEntity<>(ApiResponse.success("Market price recorded successfully", created), HttpStatus.CREATED);
    }
}
