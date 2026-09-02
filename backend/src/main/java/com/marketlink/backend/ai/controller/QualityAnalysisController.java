package com.marketlink.backend.ai.controller;

import com.marketlink.backend.ai.dto.QualityAnalysisResponse;
import com.marketlink.backend.ai.dto.RecordQualityResultRequest;
import com.marketlink.backend.ai.service.QualityAnalysisService;
import com.marketlink.backend.common.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/lots/{lotId}/quality")
@RequiredArgsConstructor
@Tag(name = "Quality Analysis", description = "Model-agnostic produce quality assessment and AI grading verification APIs")
public class QualityAnalysisController {

    private final QualityAnalysisService qualityService;

    @GetMapping
    @Operation(summary = "Get latest quality analysis", description = "Retrieves the most recent AI/laboratory quality assessment result and grade for a lot")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Quality result retrieved successfully",
                    content = @Content(schema = @Schema(implementation = QualityAnalysisResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Lot not found or no quality analysis performed yet"
            )
    })
    public ResponseEntity<ApiResponse<QualityAnalysisResponse>> getLatestQualityResult(
            @Parameter(description = "UUID of the produce lot")
            @PathVariable UUID lotId) {
        QualityAnalysisResponse response = qualityService.getLatestQualityResult(lotId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/history")
    @Operation(summary = "Get quality analysis history", description = "Retrieves all historical assessment runs for a lot")
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "200",
                    description = "Quality analysis history retrieved successfully",
                    content = @Content(array = @ArraySchema(schema = @Schema(implementation = QualityAnalysisResponse.class)))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Lot not found"
            )
    })
    public ResponseEntity<ApiResponse<List<QualityAnalysisResponse>>> getQualityHistory(
            @Parameter(description = "UUID of the produce lot")
            @PathVariable UUID lotId) {
        List<QualityAnalysisResponse> results = qualityService.getAllQualityResultsForLot(lotId);
        return ResponseEntity.ok(ApiResponse.success(results));
    }

    @PostMapping("/record")
    @Operation(summary = "Record quality analysis result", description = "Receives and maps AI model output into standardized domain quality result, transitioning lot to QUALITY_VERIFIED",
            security = @SecurityRequirement(name = "BearerAuth"))
    @ApiResponses(value = {
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "201",
                    description = "Quality analysis recorded successfully",
                    content = @Content(schema = @Schema(implementation = QualityAnalysisResponse.class))
            ),
            @io.swagger.v3.oas.annotations.responses.ApiResponse(
                    responseCode = "404",
                    description = "Lot not found"
            )
    })
    public ResponseEntity<ApiResponse<QualityAnalysisResponse>> recordQualityResult(
            @Parameter(description = "UUID of the produce lot")
            @PathVariable UUID lotId,
            @RequestBody RecordQualityResultRequest request) {
        QualityAnalysisResponse response = qualityService.recordQualityResult(lotId, request);
        return new ResponseEntity<>(ApiResponse.success("Quality analysis recorded successfully", response), HttpStatus.CREATED);
    }
}
