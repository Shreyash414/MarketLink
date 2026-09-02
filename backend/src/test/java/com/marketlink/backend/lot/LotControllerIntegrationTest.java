package com.marketlink.backend.lot;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.domain.crop.entity.Crop;
import com.marketlink.backend.domain.crop.repository.CropRepository;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.BidRepository;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.domain.user.entity.FarmerProfile;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.AccountStatus;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.enums.VerificationState;
import com.marketlink.backend.domain.user.repository.BuyerProfileRepository;
import com.marketlink.backend.domain.user.repository.FarmerProfileRepository;
import com.marketlink.backend.domain.user.repository.UserRepository;
import com.marketlink.backend.lot.dto.CreateLotRequest;
import com.marketlink.backend.lot.dto.UpdateLotRequest;
import com.marketlink.backend.security.jwt.JwtService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class LotControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private LotRepository lotRepository;

    @Autowired
    private CropRepository cropRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private FarmerProfileRepository farmerProfileRepository;

    @Autowired
    private BuyerProfileRepository buyerProfileRepository;

    @Autowired
    private BidRepository bidRepository;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private ObjectMapper objectMapper;

    private User farmerA;
    private User farmerB;
    private User buyer;
    private Crop onionCrop;

    @BeforeEach
    void setUp() {
        bidRepository.deleteAll();
        lotRepository.deleteAll();
        farmerProfileRepository.deleteAll();
        buyerProfileRepository.deleteAll();
        userRepository.deleteAll();
        cropRepository.deleteAll();

        farmerA = userRepository.save(User.builder()
                .phoneNumber("9876543210")
                .passwordHash("passHash")
                .role(Role.FARMER)
                .verificationState(VerificationState.VERIFIED)
                .accountStatus(AccountStatus.ACTIVE)
                .build());

        farmerProfileRepository.save(FarmerProfile.builder()
                .userId(farmerA.getId())
                .fullName("Farmer Ramesh")
                .district("Pune")
                .state("Maharashtra")
                .build());

        farmerB = userRepository.save(User.builder()
                .phoneNumber("9876543211")
                .passwordHash("passHash")
                .role(Role.FARMER)
                .verificationState(VerificationState.VERIFIED)
                .accountStatus(AccountStatus.ACTIVE)
                .build());

        farmerProfileRepository.save(FarmerProfile.builder()
                .userId(farmerB.getId())
                .fullName("Farmer Suresh")
                .district("Nashik")
                .state("Maharashtra")
                .build());

        buyer = userRepository.save(User.builder()
                .phoneNumber("9876543220")
                .passwordHash("passHash")
                .role(Role.BUYER)
                .verificationState(VerificationState.VERIFIED)
                .accountStatus(AccountStatus.ACTIVE)
                .build());

        onionCrop = cropRepository.save(Crop.builder()
                .name("ONION")
                .category("VEGETABLE")
                .unit("KG")
                .active(true)
                .build());
    }

    private String token(User user) {
        return "Bearer " + jwtService.generateAccessToken(user);
    }

    @Test
    @DisplayName("Farmer creates a lot, updates draft, publishes, and closes it")
    void testFullLotLifecycle() throws Exception {
        CreateLotRequest createReq = CreateLotRequest.builder()
                .cropId(onionCrop.getId())
                .variety("Nashik Red")
                .quantity(1000.0)
                .unit("KG")
                .expectedPrice(30.0)
                .minimumAcceptablePrice(25.0)
                .location("Khed, Pune")
                .build();

        // 1. Create Lot -> 201 CREATED in DRAFT status
        String respStr = mockMvc.perform(post("/api/v1/lots")
                        .header("Authorization", token(farmerA))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(createReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.status").value("DRAFT"))
                .andExpect(jsonPath("$.data.cropName").value("ONION"))
                .andReturn().getResponse().getContentAsString();

        String lotIdStr = objectMapper.readTree(respStr).path("data").path("id").asText();
        UUID lotId = UUID.fromString(lotIdStr);

        // 2. Farmer views their own lots
        mockMvc.perform(get("/api/v1/farmers/me/lots")
                        .header("Authorization", token(farmerA)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].id").value(lotIdStr));

        // 3. Update lot while in DRAFT
        UpdateLotRequest updateReq = UpdateLotRequest.builder()
                .quantity(1200.0)
                .expectedPrice(32.0)
                .build();

        mockMvc.perform(put("/api/v1/lots/" + lotId)
                        .header("Authorization", token(farmerA))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updateReq)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.quantity").value(1200.0))
                .andExpect(jsonPath("$.data.expectedPrice").value(32.0));

        // 4. Publish lot -> status becomes PUBLISHED
        mockMvc.perform(post("/api/v1/lots/" + lotId + "/publish")
                        .header("Authorization", token(farmerA)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("PUBLISHED"));

        // 5. Updating lot after publish must be rejected with 400 Bad Request
        mockMvc.perform(put("/api/v1/lots/" + lotId)
                        .header("Authorization", token(farmerA))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updateReq)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Only lots in DRAFT status can be modified"));

        // 6. Public/Buyer queries published lots
        mockMvc.perform(get("/api/v1/lots")
                        .param("cropId", onionCrop.getId().toString())
                        .header("Authorization", token(buyer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].id").value(lotIdStr));

        // 7. Farmer closes lot -> status becomes CLOSED
        mockMvc.perform(post("/api/v1/lots/" + lotId + "/close")
                        .header("Authorization", token(farmerA)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("CLOSED"));
    }

    @Test
    @DisplayName("Cross-farmer modification is forbidden (403)")
    void testCrossFarmerModificationForbidden() throws Exception {
        Lot lotB = lotRepository.save(Lot.builder()
                .farmerId(farmerB.getId())
                .cropName("ONION")
                .quantity(500.0)
                .expectedPrice(28.0)
                .status(LotStatus.DRAFT)
                .build());

        // Farmer A tries to publish Farmer B's lot -> 403 Forbidden
        mockMvc.perform(post("/api/v1/lots/" + lotB.getId() + "/publish")
                        .header("Authorization", token(farmerA)))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("Buyer cannot create a lot (403)")
    void testBuyerCannotCreateLot() throws Exception {
        CreateLotRequest createReq = CreateLotRequest.builder()
                .cropName("ONION")
                .quantity(100.0)
                .expectedPrice(25.0)
                .build();

        mockMvc.perform(post("/api/v1/lots")
                        .header("Authorization", token(buyer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(createReq)))
                .andExpect(status().isForbidden());
    }
}
