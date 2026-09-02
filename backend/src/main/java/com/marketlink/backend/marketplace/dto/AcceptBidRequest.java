package com.marketlink.backend.marketplace.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AcceptBidRequest {

    @NotNull(message = "Bid ID is required")
    private UUID bidId;

    @NotBlank(message = "Farmer transaction PIN/confirmation is required")
    private String confirmationPin;
}
