package com.marketlink.backend.profile.dto;

import com.marketlink.backend.domain.user.entity.FarmerProfile;
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
public class FarmerProfileDto {
    private UUID userId;
    private String phoneNumber;
    private Role role;
    private VerificationState verificationState;
    private AccountStatus accountStatus;
    private String fullName;
    private String village;
    private String district;
    private String state;
    private Double landHoldingAcres;
    private String preferredLanguage;

    public static FarmerProfileDto fromEntities(User user, FarmerProfile profile) {
        return FarmerProfileDto.builder()
                .userId(user.getId())
                .phoneNumber(user.getPhoneNumber())
                .role(user.getRole())
                .verificationState(user.getVerificationState())
                .accountStatus(user.getAccountStatus())
                .fullName(profile != null ? profile.getFullName() : null)
                .village(profile != null ? profile.getVillage() : null)
                .district(profile != null ? profile.getDistrict() : null)
                .state(profile != null ? profile.getState() : null)
                .landHoldingAcres(profile != null ? profile.getLandHoldingAcres() : null)
                .preferredLanguage(profile != null ? profile.getPreferredLanguage() : "en")
                .build();
    }
}
