package com.marketlink.backend.auth;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.auth.dto.LoginRequest;
import com.marketlink.backend.auth.dto.RefreshTokenRequest;
import com.marketlink.backend.auth.dto.RegisterRequest;
import com.marketlink.backend.domain.user.entity.RefreshToken;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.repository.BuyerProfileRepository;
import com.marketlink.backend.domain.user.repository.FarmerProfileRepository;
import com.marketlink.backend.domain.user.repository.RefreshTokenRepository;
import com.marketlink.backend.domain.user.repository.UserRepository;
import com.marketlink.backend.security.ratelimit.AuthRateLimitingFilter;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AuthFlowTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private FarmerProfileRepository farmerProfileRepository;

    @Autowired
    private BuyerProfileRepository buyerProfileRepository;

    @Autowired
    private RefreshTokenRepository refreshTokenRepository;

    @Autowired
    private AuthRateLimitingFilter rateLimitingFilter;

    @Autowired
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        rateLimitingFilter.resetForTesting();
        refreshTokenRepository.deleteAll();
        farmerProfileRepository.deleteAll();
        buyerProfileRepository.deleteAll();
        userRepository.deleteAll();
    }

    @Test
    @DisplayName("Complete Registration, Login, Token Rotation and Logout Revocation Flow")
    void testRegistrationLoginAndRevocationFlow() throws Exception {
        RegisterRequest registerReq = RegisterRequest.builder()
                .phoneNumber("9876501234")
                .password("securePass123")
                .role(Role.FARMER)
                .fullName("Ramesh Kumar")
                .village("Khed")
                .district("Pune")
                .state("Maharashtra")
                .build();

        // 1. Register basic user
        String regResponseStr = mockMvc.perform(post("/api/v1/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(registerReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.accessToken").isString())
                .andExpect(jsonPath("$.data.refreshToken").isString())
                .andExpect(jsonPath("$.data.user.verificationState").value("UNVERIFIED"))
                .andExpect(jsonPath("$.data.user.accountStatus").value("ACTIVE"))
                .andExpect(jsonPath("$.data.user.passwordHash").doesNotExist())
                .andReturn().getResponse().getContentAsString();

        String accessToken = objectMapper.readTree(regResponseStr).path("data").path("accessToken").asText();
        String initialRefreshToken = objectMapper.readTree(regResponseStr).path("data").path("refreshToken").asText();

        // 2. Fetch profile via /auth/me
        mockMvc.perform(get("/api/v1/auth/me")
                        .header("Authorization", "Bearer " + accessToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.phoneNumber").value("9876501234"))
                .andExpect(jsonPath("$.data.verificationState").value("UNVERIFIED"))
                .andExpect(jsonPath("$.data.passwordHash").doesNotExist());

        // 3. Login with credentials
        LoginRequest loginReq = LoginRequest.builder()
                .phoneNumber("9876501234")
                .password("securePass123")
                .build();

        String loginRespStr = mockMvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(loginReq)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.accessToken").isString())
                .andReturn().getResponse().getContentAsString();

        String loginRefreshToken = objectMapper.readTree(loginRespStr).path("data").path("refreshToken").asText();

        // 4. Refresh token rotation: exchanges token for fresh pair
        RefreshTokenRequest refreshReq = RefreshTokenRequest.builder()
                .refreshToken(loginRefreshToken)
                .build();

        String rotatedRespStr = mockMvc.perform(post("/api/v1/auth/refresh")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(refreshReq)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.accessToken").isString())
                .andExpect(jsonPath("$.data.refreshToken").isString())
                .andReturn().getResponse().getContentAsString();

        String newRefreshToken = objectMapper.readTree(rotatedRespStr).path("data").path("refreshToken").asText();
        String newAccessToken = objectMapper.readTree(rotatedRespStr).path("data").path("accessToken").asText();

        // 5. Old refresh token should now be REVOKED (single-use rotation)
        mockMvc.perform(post("/api/v1/auth/refresh")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(refreshReq)))
                .andExpect(status().isUnauthorized());

        // 6. Logout should revoke all active refresh tokens for the user
        mockMvc.perform(post("/api/v1/auth/logout")
                        .header("Authorization", "Bearer " + newAccessToken))
                .andExpect(status().isOk());

        // Attempting to refresh using rotated token after logout must fail
        RefreshTokenRequest postLogoutRefreshReq = RefreshTokenRequest.builder()
                .refreshToken(newRefreshToken)
                .build();

        mockMvc.perform(post("/api/v1/auth/refresh")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(postLogoutRefreshReq)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("Role Escalation Prevention: User cannot register as ADMIN")
    void testRoleEscalation_adminRegistrationForbidden() throws Exception {
        RegisterRequest adminReq = RegisterRequest.builder()
                .phoneNumber("9876509999")
                .password("adminPass123")
                .role(Role.ADMIN)
                .fullName("Attacker")
                .build();

        mockMvc.perform(post("/api/v1/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(adminReq)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Public registration is only permitted for FARMER and BUYER roles"));
    }

    @Test
    @DisplayName("Rate Limiting: Exceeding auth limit returns 429 Too Many Requests")
    void testAuthRateLimiting() throws Exception {
        LoginRequest badLogin = LoginRequest.builder()
                .phoneNumber("9999999999")
                .password("wrongpassword")
                .build();

        // Perform 15 requests (allowed within window)
        for (int i = 0; i < 15; i++) {
            mockMvc.perform(post("/api/v1/auth/login")
                            .header("X-Forwarded-For", "192.168.1.100")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(badLogin)))
                    .andExpect(status().isUnauthorized());
        }

        // 16th request from same IP must be rate-limited with 429
        mockMvc.perform(post("/api/v1/auth/login")
                        .header("X-Forwarded-For", "192.168.1.100")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(badLogin)))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.message").value("Too many authentication attempts. Please try again in one minute."));
    }
}
