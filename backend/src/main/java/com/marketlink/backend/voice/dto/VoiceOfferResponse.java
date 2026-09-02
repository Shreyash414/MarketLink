package com.marketlink.backend.voice.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

import java.util.UUID;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Voice/IVR response payload for farmer pending offer inquiries")
public class VoiceOfferResponse {

    @Schema(description = "UUID of the offer", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private UUID offerId;

    @Schema(description = "UUID of the lot", example = "b2c3d4e5-f6a7-8901-bcde-f12345678901")
    private UUID lotId;

    @Schema(description = "Crop name", example = "ONION")
    private String cropName;

    @Schema(description = "Buyer business name", example = "Agro Fresh Trading")
    private String buyerBusinessName;

    @Schema(description = "Offered price in Rupees", example = "34.0")
    private Double offeredPrice;

    @Schema(description = "Quantity requested", example = "500.0")
    private Double quantity;

    @Schema(description = "Unit", example = "KG")
    private String unit;

    @Schema(description = "Voice-synthesizer-friendly text description",
            example = "You have received an offer from Agro Fresh Trading for 500 KG of ONION at 34 Rupees per KG. Press 1 to accept or 2 to reject.")
    private String voiceSummary;
}
