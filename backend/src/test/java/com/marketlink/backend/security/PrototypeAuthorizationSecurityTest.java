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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@TestPropertySource(properties = "marketlink.security.prototype-mode=true")
class PrototypeAuthorizationSecurityTest {

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
                .fullName("Prototype Farmer")
                .village("Khed")
                .district("Pune")
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
    // 1. Anonymous cannot access News
    // =========================================================================
    @Test
    @DisplayName("1. Anonymous cannot access News - returns 401")
    void test1_anonymousCannotAccessNews() throws Exception {
        mockMvc.perform(get("/api/v1/news"))
                .andExpect(status().isUnauthorized());
    }

    // =========================================================================
    // 2. Anonymous cannot access FAQs
    // =========================================================================
    @Test
    @DisplayName("2. Anonymous cannot access FAQs - returns 401")
    void test2_anonymousCannotAccessFaqs() throws Exception {
        mockMvc.perform(get("/api/v1/faqs"))
                .andExpect(status().isUnauthorized());
    }

    // =========================================================================
    // 3. Anonymous cannot access marketplace
    // =========================================================================
    @Test
    @DisplayName("3. Anonymous cannot access marketplace - returns 401")
    void test3_anonymousCannotAccessMarketplace() throws Exception {
        mockMvc.perform(get("/api/v1/marketplace/browse/lots"))
                .andExpect(status().isUnauthorized());

        CreateLotRequest lotReq = CreateLotRequest.builder()
                .cropName("Wheat")
                .quantityKg(100.0)
                .basePricePerKg(25.0)
                .build();

        mockMvc.perform(post("/api/v1/marketplace/lots")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(lotReq)))
                .andExpect(status().isUnauthorized());
    }

    // =========================================================================
    // 4. Authenticated active FARMER can access farmer marketplace while UNVERIFIED
    // =========================================================================
    @Test
    @DisplayName("4. Authenticated active FARMER can access farmer marketplace while verificationState = UNVERIFIED")
    void test4_unverifiedFarmerCanAccessMarketplaceInPrototypeMode() throws Exception {
        User farmer = createFarmer("9876543210", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);

        // Verification state is UNVERIFIED
        assertThat(farmer.getVerificationState()).isEqualTo(VerificationState.UNVERIFIED);

        CreateLotRequest lotReq = CreateLotRequest.builder()
                .cropName("Cotton")
                .variety("Bt-Cotton")
                .quantityKg(1500.0)
                .basePricePerKg(60.0)
                .location("Akola")
                .build();

        // 1. Create Lot (201 Created)
        String responseContent = mockMvc.perform(post("/api/v1/marketplace/lots")
                        .header("Authorization", token(farmer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(lotReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.cropName").value("Cotton"))
                .andReturn().getResponse().getContentAsString();

        String lotIdStr = objectMapper.readTree(responseContent).path("data").path("id").asText();

        // 2. Publish Lot (200 OK)
        mockMvc.perform(put("/api/v1/marketplace/lots/" + lotIdStr + "/publish")
                        .header("Authorization", token(farmer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("PUBLISHED"));

        // 3. View own lots (200 OK)
        mockMvc.perform(get("/api/v1/marketplace/lots/my")
                        .header("Authorization", token(farmer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data").isArray());
    }

    // =========================================================================
    // 5. Authenticated active BUYER can access buyer marketplace while UNVERIFIED
    // =========================================================================
    @Test
    @DisplayName("5. Authenticated active BUYER can access buyer marketplace while verificationState = UNVERIFIED")
    void test5_unverifiedBuyerCanAccessMarketplaceInPrototypeMode() throws Exception {
        User buyer = createBuyer("9876543211", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);
        User farmer = createFarmer("9876543210", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);

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

        // 1. Browse lots (200 OK)
        mockMvc.perform(get("/api/v1/marketplace/browse/lots")
                        .header("Authorization", token(buyer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data").isArray());

        // 2. Place bid (201 Created)
        mockMvc.perform(post("/api/v1/marketplace/bids")
                        .header("Authorization", token(buyer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(bidReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.offeredPricePerKg").value(26.0));

        // 3. View own bids (200 OK)
        mockMvc.perform(get("/api/v1/marketplace/bids/my")
                        .header("Authorization", token(buyer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data").isArray());
    }

    // =========================================================================
    // 6. FARMER cannot access buyer-only APIs
    // =========================================================================
    @Test
    @DisplayName("6. FARMER cannot access buyer-only APIs - returns 403")
    void test6_farmerCannotAccessBuyerOnlyApis() throws Exception {
        User farmer = createFarmer("9876543210", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);

        mockMvc.perform(get("/api/v1/buyers/me")
                        .header("Authorization", token(farmer)))
                .andExpect(status().isForbidden());

        CreateBidRequest bidReq = CreateBidRequest.builder()
                .lotId(java.util.UUID.randomUUID())
                .offeredPricePerKg(30.0)
                .totalQuantityKg(100.0)
                .build();

        mockMvc.perform(post("/api/v1/marketplace/bids")
                        .header("Authorization", token(farmer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(bidReq)))
                .andExpect(status().isForbidden());
    }

    // =========================================================================
    // 7. BUYER cannot access farmer-only APIs
    // =========================================================================
    @Test
    @DisplayName("7. BUYER cannot access farmer-only APIs - returns 403")
    void test7_buyerCannotAccessFarmerOnlyApis() throws Exception {
        User buyer = createBuyer("9876543211", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);

        mockMvc.perform(get("/api/v1/farmers/me")
                        .header("Authorization", token(buyer)))
                .andExpect(status().isForbidden());

        CreateLotRequest lotReq = CreateLotRequest.builder()
                .cropName("Tomato")
                .quantityKg(200.0)
                .basePricePerKg(15.0)
                .build();

        mockMvc.perform(post("/api/v1/marketplace/lots")
                        .header("Authorization", token(buyer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(lotReq)))
                .andExpect(status().isForbidden());
    }

    // =========================================================================
    // 8. DISABLED FARMER cannot access marketplace
    // =========================================================================
    @Test
    @DisplayName("8. DISABLED FARMER cannot access marketplace - returns 401/403")
    void test8_disabledFarmerCannotAccessMarketplace() throws Exception {
        User disabledFarmer = createFarmer("9876543210", VerificationState.UNVERIFIED, AccountStatus.DISABLED);

        mockMvc.perform(get("/api/v1/marketplace/lots/my")
                        .header("Authorization", token(disabledFarmer)))
                .andExpect(status().isUnauthorized());
    }

    // =========================================================================
    // 9. LOCKED FARMER cannot access marketplace
    // =========================================================================
    @Test
    @DisplayName("9. LOCKED FARMER cannot access marketplace - returns 401/403")
    void test9_lockedFarmerCannotAccessMarketplace() throws Exception {
        User lockedFarmer = createFarmer("9876543210", VerificationState.UNVERIFIED, AccountStatus.LOCKED);

        mockMvc.perform(get("/api/v1/marketplace/lots/my")
                        .header("Authorization", token(lockedFarmer)))
                .andExpect(status().isUnauthorized());
    }

    // =========================================================================
    // 10. Client cannot modify verificationState
    // =========================================================================
    @Test
    @DisplayName("10. Client cannot modify verificationState")
    void test10_clientCannotModifyVerificationState() throws Exception {
        User farmer = createFarmer("9876543210", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);

        String maliciousPayload = "{\"fullName\":\"Hacker\",\"verificationState\":\"VERIFIED\"}";

        mockMvc.perform(put("/api/v1/farmers/me")
                        .header("Authorization", token(farmer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(maliciousPayload))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.verificationState").value("UNVERIFIED"));

        User userInDb = userRepository.findById(farmer.getId()).orElseThrow();
        assertThat(userInDb.getVerificationState()).isEqualTo(VerificationState.UNVERIFIED);
    }

    // =========================================================================
    // 11. Prototype mode does not modify verificationState
    // =========================================================================
    @Test
    @DisplayName("11. Prototype mode does not modify verificationState in DB")
    void test11_prototypeModeDoesNotModifyVerificationState() throws Exception {
        User farmer = createFarmer("9876543210", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);

        CreateLotRequest lotReq = CreateLotRequest.builder()
                .cropName("Soybean")
                .quantityKg(100.0)
                .basePricePerKg(40.0)
                .build();

        // Marketplace access succeeded in prototype mode
        mockMvc.perform(post("/api/v1/marketplace/lots")
                        .header("Authorization", token(farmer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(lotReq)))
                .andExpect(status().isCreated());

        // Verification state in DB remains genuinely UNVERIFIED
        User userInDb = userRepository.findById(farmer.getId()).orElseThrow();
        assertThat(userInDb.getVerificationState()).isEqualTo(VerificationState.UNVERIFIED);
    }

    // =========================================================================
    // 12. Cross-user resource access remains denied
    // =========================================================================
    @Test
    @DisplayName("12. Cross-user resource access remains denied - returns 403")
    void test12_crossUserResourceAccessDenied() throws Exception {
        User farmerA = createFarmer("9876543210", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);
        User farmerB = createFarmer("9876543219", VerificationState.UNVERIFIED, AccountStatus.ACTIVE);

        Lot lotB = lotRepository.save(Lot.builder()
                .farmerId(farmerB.getId())
                .cropName("Ginger")
                .quantityKg(300.0)
                .basePricePerKg(80.0)
                .status(LotStatus.DRAFT)
                .build());

        // Farmer A cannot publish Farmer B's lot -> 403
        mockMvc.perform(put("/api/v1/marketplace/lots/" + lotB.getId() + "/publish")
                        .header("Authorization", token(farmerA)))
                .andExpect(status().isForbidden());
    }
}
