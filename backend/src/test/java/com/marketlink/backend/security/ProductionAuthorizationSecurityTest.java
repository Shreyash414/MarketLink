package com.marketlink.backend.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.BidRepository;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.domain.user.entity.BuyerProfile;
import com.marketlink.backend.domain.user.entity.FarmerProfile;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.AccountStatus;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.enums.VerificationState;
import com.marketlink.backend.domain.user.repository.BuyerProfileRepository;
import com.marketlink.backend.domain.user.repository.FarmerProfileRepository;
import com.marketlink.backend.domain.user.repository.UserRepository;
import com.marketlink.backend.marketplace.dto.CreateBidRequest;
import com.marketlink.backend.marketplace.dto.CreateLotRequest;
import com.marketlink.backend.security.jwt.JwtService;
import com.marketlink.backend.security.ratelimit.AuthRateLimitingFilter;
import com.marketlink.backend.verification.dto.UidaiStartRequest;
import com.marketlink.backend.verification.dto.UidaiVerifyOtpRequest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@TestPropertySource(properties = "marketlink.security.prototype-mode=false")
class ProductionAuthorizationSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private FarmerProfileRepository farmerProfileRepository;

    @Autowired
    private BuyerProfileRepository buyerProfileRepository;

    @Autowired
    private LotRepository lotRepository;

    @Autowired
    private BidRepository bidRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthRateLimitingFilter rateLimitingFilter;

    @Autowired
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        rateLimitingFilter.resetForTesting();
        bidRepository.deleteAll();
        lotRepository.deleteAll();
        farmerProfileRepository.deleteAll();
        buyerProfileRepository.deleteAll();
        userRepository.deleteAll();
    }

    private User createFarmer(String phone, VerificationState state, AccountStatus status) {
        User user = userRepository.save(User.builder()
                .phoneNumber(phone)
                .passwordHash(passwordEncoder.encode("password123"))
                .role(Role.FARMER)
                .verificationState(state)
                .accountStatus(status)
                .build());

        farmerProfileRepository.save(FarmerProfile.builder()
                .userId(user.getId())
                .fullName("Production Farmer")
                .village("Sample Village")
                .district("Nashik")
                .state("Maharashtra")
                .build());

        return user;
    }

    private User createBuyer(String phone, VerificationState state, AccountStatus status) {
        User user = userRepository.save(User.builder()
                .phoneNumber(phone)
                .passwordHash(passwordEncoder.encode("password123"))
                .role(Role.BUYER)
                .verificationState(state)
                .accountStatus(status)
                .build());

        buyerProfileRepository.save(BuyerProfile.builder()
                .userId(user.getId())
                .businessName("Agri Traders Corp")
                .district("Pune")
                .state("Maharashtra")
                .build());

        return user;
    }

    private String token(User user) {
        return "Bearer " + jwtService.generateAccessToken(user);
    }

    // =========================================================================
    // 1. With prototype mode disabled, UNVERIFIED FARMER is denied marketplace access
    // =========================================================================
    @Test
    @DisplayName("1. Production Mode: UNVERIFIED FARMER is denied marketplace access - returns 403")
    void test1_unverifiedFarmerDeniedInProductionMode() throws Exception {
        User farmer = createFarmer("9876543210", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);

        CreateLotRequest lotReq = CreateLotRequest.builder()
                .cropName("Soybean")
                .variety("JS-335")
                .quantityKg(500.0)
                .basePricePerKg(45.0)
                .location("Nashik")
                .build();

        mockMvc.perform(post("/api/v1/marketplace/lots")
                        .header("Authorization", token(farmer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(lotReq)))
                .andExpect(status().isForbidden());
    }

    // =========================================================================
    // 2. With prototype mode disabled, UNVERIFIED BUYER is denied marketplace access
    // =========================================================================
    @Test
    @DisplayName("2. Production Mode: UNVERIFIED BUYER is denied marketplace access - returns 403")
    void test2_unverifiedBuyerDeniedInProductionMode() throws Exception {
        User buyer = createBuyer("9876543211", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);
        User verifiedFarmer = createFarmer("9876543212", VerificationState.VERIFIED, AccountStatus.ACTIVE);

        Lot lot = lotRepository.save(Lot.builder()
                .farmerId(verifiedFarmer.getId())
                .cropName("Onion")
                .quantityKg(2000.0)
                .basePricePerKg(20.0)
                .status(LotStatus.PUBLISHED)
                .build());

        CreateBidRequest bidReq = CreateBidRequest.builder()
                .lotId(lot.getId())
                .offeredPricePerKg(22.0)
                .totalQuantityKg(2000.0)
                .build();

        mockMvc.perform(post("/api/v1/marketplace/bids")
                        .header("Authorization", token(buyer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(bidReq)))
                .andExpect(status().isForbidden());
    }

    // =========================================================================
    // 3. With prototype mode disabled, VERIFIED FARMER is allowed marketplace access
    // =========================================================================
    @Test
    @DisplayName("3. Production Mode: VERIFIED FARMER is allowed marketplace access - returns 201")
    void test3_verifiedFarmerAllowedInProductionMode() throws Exception {
        User farmer = createFarmer("9876543210", VerificationState.VERIFIED, AccountStatus.ACTIVE);

        CreateLotRequest lotReq = CreateLotRequest.builder()
                .cropName("Cotton")
                .variety("Bt-Cotton")
                .quantityKg(1500.0)
                .basePricePerKg(60.0)
                .location("Akola")
                .build();

        mockMvc.perform(post("/api/v1/marketplace/lots")
                        .header("Authorization", token(farmer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(lotReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.cropName").value("Cotton"));
    }

    // =========================================================================
    // 4. With prototype mode disabled, VERIFIED BUYER is allowed marketplace access
    // =========================================================================
    @Test
    @DisplayName("4. Production Mode: VERIFIED BUYER is allowed marketplace access - returns 201")
    void test4_verifiedBuyerAllowedInProductionMode() throws Exception {
        User buyer = createBuyer("9876543211", VerificationState.VERIFIED, AccountStatus.ACTIVE);
        User farmer = createFarmer("9876543210", VerificationState.VERIFIED, AccountStatus.ACTIVE);

        Lot lot = lotRepository.save(Lot.builder()
                .farmerId(farmer.getId())
                .cropName("Wheat")
                .quantityKg(500.0)
                .basePricePerKg(25.0)
                .status(LotStatus.PUBLISHED)
                .build());

        CreateBidRequest bidReq = CreateBidRequest.builder()
                .lotId(lot.getId())
                .offeredPricePerKg(26.0)
                .totalQuantityKg(500.0)
                .build();

        mockMvc.perform(post("/api/v1/marketplace/bids")
                        .header("Authorization", token(buyer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(bidReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.offeredPricePerKg").value(26.0));
    }

    // =========================================================================
    // 5. UIDAI verification transitions user to VERIFIED and unlocks marketplace
    // =========================================================================
    @Test
    @DisplayName("5. Production Mode: UIDAI verification transitions user to VERIFIED and unlocks marketplace")
    void test5_uidaiVerificationUnlocksMarketplaceInProductionMode() throws Exception {
        User farmer = createFarmer("9876543210", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);

        // 1. Initially blocked (403)
        CreateLotRequest lotReq = CreateLotRequest.builder()
                .cropName("Maize")
                .quantityKg(800.0)
                .basePricePerKg(18.0)
                .build();

        mockMvc.perform(post("/api/v1/marketplace/lots")
                        .header("Authorization", token(farmer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(lotReq)))
                .andExpect(status().isForbidden());

        // 2. Start UIDAI verification
        UidaiStartRequest startReq = UidaiStartRequest.builder()
                .aadhaarNumber("123456789012")
                .consent(true)
                .build();

        String startRespStr = mockMvc.perform(post("/api/v1/verification/uidai/start")
                        .header("Authorization", token(farmer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(startReq)))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();

        String txnId = objectMapper.readTree(startRespStr).path("data").path("transactionId").asText();

        // 3. Verify OTP
        UidaiVerifyOtpRequest verifyReq = UidaiVerifyOtpRequest.builder()
                .transactionId(txnId)
                .otp("123456")
                .build();

        mockMvc.perform(post("/api/v1/verification/uidai/verify-otp")
                        .header("Authorization", token(farmer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(verifyReq)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.verificationState").value("VERIFIED"));

        User verifiedUser = userRepository.findById(farmer.getId()).orElseThrow();
        assertThat(verifiedUser.getVerificationState()).isEqualTo(VerificationState.VERIFIED);

        // 4. Now marketplace access is unlocked (201 Created)
        mockMvc.perform(post("/api/v1/marketplace/lots")
                        .header("Authorization", token(verifiedUser))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(lotReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.cropName").value("Maize"));
    }
}
