package com.marketlink.backend.auth.dto;

import com.marketlink.backend.domain.user.enums.Role;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RegisterRequest {

    @NotBlank(message = "Phone number is required")
    @Pattern(regexp = "^[6-9]\\d{9}$", message = "Must be a valid 10-digit Indian phone number")
    private String phoneNumber;

    @NotBlank(message = "Password is required")
    @Size(min = 6, message = "Password must be at least 6 characters")
    private String password;

    @NotNull(message = "Role is required (FARMER or BUYER)")
    private Role role;

    @NotBlank(message = "Full name / business name is required")
    private String fullName;

    // Optional location fields for initial profile setup
    private String village;
    private String district;
    private String state;
    private String gstin;

    // Notice: Any verificationState or accountStatus sent by client will be IGNORED by backend!
}
