package com.marketlink.backend.auth.dto;

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
public class SafeUserProfileDto {
    private UUID id;
    private String phoneNumber;
    private Role role;
    private VerificationState verificationState;
    private AccountStatus accountStatus;

    public static SafeUserProfileDto fromUser(User user) {
        return SafeUserProfileDto.builder()
                .id(user.getId())
                .phoneNumber(user.getPhoneNumber())
                .role(user.getRole())
                .verificationState(user.getVerificationState())
                .accountStatus(user.getAccountStatus())
                .build();
    }
}
