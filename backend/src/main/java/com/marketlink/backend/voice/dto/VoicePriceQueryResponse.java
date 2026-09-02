package com.marketlink.backend.voice.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.time.LocalDate;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Voice/IVR response payload for price inquiries")
public class VoicePriceQueryResponse {

    @Schema(description = "Crop name", example = "ONION")
    private String cropName;

    @Schema(description = "Market name", example = "Pune APMC")
    private String marketName;

    @Schema(description = "Modal price in Rupees", example = "2400.0")
    private Double modalPrice;

    @Schema(description = "Unit of measurement", example = "QUINTAL")
    private String unit;

    @Schema(description = "Date of price observation", example = "2026-09-01")
    private LocalDate priceDate;

    @Schema(description = "Voice-synthesizer-friendly text description",
            example = "The modal price of ONION at Pune APMC is 2400 Rupees per QUINTAL on 2026-09-01.")
    private String voiceSummary;
}
