package com.marketlink.backend.profile.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UpdateBuyerProfileRequest {
    private String businessName;
    private String gstin;
    private String district;
    private String state;
    private String tradeCategory;

    // Notice: verificationState, role, and accountStatus are strictly omitted.
}
