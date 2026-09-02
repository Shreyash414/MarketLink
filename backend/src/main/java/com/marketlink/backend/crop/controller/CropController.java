package com.marketlink.backend.crop.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.crop.dto.CreateCropRequest;
import com.marketlink.backend.crop.dto.CropResponse;
import com.marketlink.backend.crop.dto.UpdateCropRequest;
import com.marketlink.backend.crop.service.CropService;
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
@RequestMapping("/api/v1/crops")
@RequiredArgsConstructor
@Tag(name = "Crops", description = "Crop master data APIs for produce listing, classification, and price discovery")
public class CropController {

    private final CropService cropService;

    @GetMapping
    @Operation(summary = "Get all crops", description = "Retrieves master crops with optional filters for active status and category")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Crops retrieved successfully",
                    content = @Content(array = @ArraySchema(schema = @Schema(implementation = CropResponse.class)))
            )
    })
    public ResponseEntity<ApiResponse<List<CropResponse>>> getAllCrops(
            @Parameter(description = "Filter only active crops (defaults to true)")
            @RequestParam(required = false, defaultValue = "true") Boolean activeOnly,
            @Parameter(description = "Filter by crop category (e.g., VEGETABLE, GRAIN, PULSE)")
            @RequestParam(required = false) String category) {
        List<CropResponse> crops = cropService.getAllCrops(activeOnly, category);
        return ResponseEntity.ok(ApiResponse.success(crops));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get crop by ID", description = "Retrieves a single crop master record by its unique UUID")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Crop retrieved successfully",
                    content = @Content(schema = @Schema(implementation = CropResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Crop not found with provided UUID"
            )
    })
    public ResponseEntity<ApiResponse<CropResponse>> getCropById(
            @Parameter(description = "Unique UUID of the crop")
            @PathVariable UUID id) {
        CropResponse crop = cropService.getCropById(id);
        return ResponseEntity.ok(ApiResponse.success(crop));
    }

    @PostMapping
    @Operation(summary = "Create crop", description = "Creates a new master crop entity in the catalog",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "201",
                    description = "Crop created successfully",
                    content = @Content(schema = @Schema(implementation = CropResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "Invalid payload or validation failed"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "409",
                    description = "Crop with this name already exists"
            )
    })
    public ResponseEntity<ApiResponse<CropResponse>> createCrop(
            @Valid @RequestBody CreateCropRequest request) {
        CropResponse created = cropService.createCrop(request);
        return new ResponseEntity<>(ApiResponse.success("Crop created successfully", created), HttpStatus.CREATED);
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update crop", description = "Updates details or active status of an existing crop",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Crop updated successfully",
                    content = @Content(schema = @Schema(implementation = CropResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Crop not found"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "409",
                    description = "Crop name conflicts with an existing crop"
            )
    })
    public ResponseEntity<ApiResponse<CropResponse>> updateCrop(
            @Parameter(description = "Unique UUID of the crop to update")
            @PathVariable UUID id,
            @Valid @RequestBody UpdateCropRequest request) {
        CropResponse updated = cropService.updateCrop(id, request);
        return ResponseEntity.ok(ApiResponse.success("Crop updated successfully", updated));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete crop", description = "Permanently removes a crop master record",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Crop deleted successfully"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Crop not found"
            )
    })
    public ResponseEntity<ApiResponse<Void>> deleteCrop(
            @Parameter(description = "Unique UUID of the crop to delete")
            @PathVariable UUID id) {
        cropService.deleteCrop(id);
        return ResponseEntity.ok(ApiResponse.success("Crop deleted successfully", null));
    }
}
