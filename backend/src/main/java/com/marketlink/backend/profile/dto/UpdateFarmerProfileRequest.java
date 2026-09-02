package com.marketlink.backend.profile.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UpdateFarmerProfileRequest {
    private String fullName;
    private String village;
    private String district;
    private String state;
    private Double landHoldingAcres;
    private String preferredLanguage;

    // Notice: verificationState, role, and accountStatus are strictly omitted.
}
