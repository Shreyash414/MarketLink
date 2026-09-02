package com.marketlink.backend.verification.dto;

import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UidaiStartRequest {

    @NotBlank(message = "Aadhaar number or reference is required")
    @Pattern(regexp = "^\\d{12}$", message = "Aadhaar must be a 12-digit number")
    private String aadhaarNumber;

    @AssertTrue(message = "Explicit user consent is mandatory for UIDAI verification")
    private boolean consent;
}
