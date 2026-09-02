package com.marketlink.backend.verification.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UidaiStartResponse {
    private String transactionId;
    private String status;
    private String message;
}
