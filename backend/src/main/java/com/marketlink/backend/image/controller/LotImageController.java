package com.marketlink.backend.image.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.domain.image.entity.LotImage;
import com.marketlink.backend.image.dto.LotImageResponse;
import com.marketlink.backend.image.service.LotImageService;
import com.marketlink.backend.security.principal.UserPrincipal;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/lots/{lotId}/images")
@RequiredArgsConstructor
@Tag(name = "Lot Images", description = "Crop photo upload, optimized JPEG compression, and direct binary image streaming APIs")
public class LotImageController {

    private final LotImageService lotImageService;

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id) and @marketplaceAuth.isLotOwner(principal.id, #lotId)")
    @Operation(summary = "Upload lot photo", description = "Farmer uploads a crop photograph. The photo is automatically validated, aspect-ratio resized, and JPEG compressed.",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "201",
                    description = "Photo compressed and metadata stored successfully",
                    content = @Content(schema = @Schema(implementation = LotImageResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "400",
                    description = "Invalid image file or compression limit exceeded"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller does not own this lot"
            )
    })
    public ResponseEntity<ApiResponse<LotImageResponse>> uploadImage(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the lot to attach image to")
            @PathVariable UUID lotId,
            @Parameter(description = "Image file (JPEG, PNG, WEBP, BMP)")
            @RequestParam("file") MultipartFile file,
            @Parameter(description = "Optional image category/purpose", example = "PRODUCE_PHOTO")
            @RequestParam(value = "imageType", required = false) String imageType) {
        LotImageResponse response = lotImageService.uploadLotImage(principal.getId(), lotId, file, imageType);
        return new ResponseEntity<>(ApiResponse.success("Photo uploaded and compressed successfully", response), HttpStatus.CREATED);
    }

    @GetMapping
    @Operation(summary = "Get lot images metadata", description = "Retrieves metadata and direct stream URLs for all photos attached to a lot")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Image metadata list retrieved successfully",
                    content = @Content(array = @ArraySchema(schema = @Schema(implementation = LotImageResponse.class)))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Lot not found"
            )
    })
    public ResponseEntity<ApiResponse<List<LotImageResponse>>> getLotImages(
            @Parameter(description = "UUID of the lot")
            @PathVariable UUID lotId) {
        List<LotImageResponse> images = lotImageService.getLotImages(lotId);
        return ResponseEntity.ok(ApiResponse.success(images));
    }

    @GetMapping("/{imageId}")
    @Operation(summary = "Stream raw binary image", description = "Directly returns the compressed binary image with Content-Type: image/jpeg for fast mobile / browser display")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Raw JPEG binary stream",
                    content = @Content(mediaType = "image/jpeg")
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Image not found"
            )
    })
    public ResponseEntity<byte[]> streamImage(
            @Parameter(description = "UUID of the lot")
            @PathVariable UUID lotId,
            @Parameter(description = "UUID of the image")
            @PathVariable UUID imageId) {
        LotImage image = lotImageService.getImageEntity(lotId, imageId);

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, MediaType.IMAGE_JPEG_VALUE)
                .header(HttpHeaders.CACHE_CONTROL, "private, max-age=3600")
                .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + image.getOriginalFilename() + "\"")
                .body(image.getImageData().getData());
    }

    @DeleteMapping("/{imageId}")
    @PreAuthorize("@marketplaceAuth.isVerifiedFarmer(principal.id) and @marketplaceAuth.isLotOwner(principal.id, #lotId)")
    @Operation(summary = "Delete lot photo", description = "Farmer removes a photograph from their lot",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Image deleted successfully"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "403",
                    description = "Forbidden: Caller does not own this lot"
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Image not found"
            )
    })
    public ResponseEntity<ApiResponse<Void>> deleteImage(
            @AuthenticationPrincipal UserPrincipal principal,
            @Parameter(description = "UUID of the lot")
            @PathVariable UUID lotId,
            @Parameter(description = "UUID of the image to delete")
            @PathVariable UUID imageId) {
        lotImageService.deleteLotImage(principal.getId(), lotId, imageId);
        return ResponseEntity.ok(ApiResponse.success("Image deleted successfully", null));
    }
}
