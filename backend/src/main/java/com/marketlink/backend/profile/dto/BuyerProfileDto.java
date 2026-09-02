package com.marketlink.backend.profile.dto;

import com.marketlink.backend.domain.user.entity.BuyerProfile;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.AccountStatus;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.enums.VerificationState;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BuyerProfileDto {
    private UUID userId;
    private String phoneNumber;
    private Role role;
    private VerificationState verificationState;
    private AccountStatus accountStatus;
    private String businessName;
    private String gstin;
    private String district;
    private String state;
    private String tradeCategory;

    public static BuyerProfileDto fromEntities(User user, BuyerProfile profile) {
        return BuyerProfileDto.builder()
                .userId(user.getId())
                .phoneNumber(user.getPhoneNumber())
                .role(user.getRole())
                .verificationState(user.getVerificationState())
                .accountStatus(user.getAccountStatus())
                .businessName(profile != null ? profile.getBusinessName() : null)
                .gstin(profile != null ? profile.getGstin() : null)
                .district(profile != null ? profile.getDistrict() : null)
                .state(profile != null ? profile.getState() : null)
                .tradeCategory(profile != null ? profile.getTradeCategory() : null)
                .build();
    }
}
