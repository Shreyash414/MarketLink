package com.marketlink.backend.ai;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.ai.dto.RecordQualityResultRequest;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.BidRepository;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.domain.quality.repository.QualityAnalysisResultRepository;
import com.marketlink.backend.domain.user.entity.FarmerProfile;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.AccountStatus;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.enums.VerificationState;
import com.marketlink.backend.domain.user.repository.BuyerProfileRepository;
import com.marketlink.backend.domain.user.repository.FarmerProfileRepository;
import com.marketlink.backend.domain.user.repository.UserRepository;
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

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class QualityAnalysisControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private QualityAnalysisResultRepository qualityRepository;

    @Autowired
    private LotRepository lotRepository;

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

    private User farmer;
    private Lot testLot;

    @BeforeEach
    void setUp() {
        qualityRepository.deleteAll();
        bidRepository.deleteAll();
        lotRepository.deleteAll();
        farmerProfileRepository.deleteAll();
        buyerProfileRepository.deleteAll();
        userRepository.deleteAll();

        farmer = userRepository.save(User.builder()
                .phoneNumber("9876543210")
                .passwordHash("passHash")
                .role(Role.FARMER)
                .verificationState(VerificationState.VERIFIED)
                .accountStatus(AccountStatus.ACTIVE)
                .build());

        farmerProfileRepository.save(FarmerProfile.builder()
                .userId(farmer.getId())
                .fullName("Farmer Ramesh")
                .district("Pune")
                .state("Maharashtra")
                .build());

        testLot = lotRepository.save(Lot.builder()
                .farmerId(farmer.getId())
                .cropName("ONION")
                .quantity(500.0)
                .expectedPrice(30.0)
                .status(LotStatus.DRAFT)
                .build());
    }

    private String token(User user) {
        return "Bearer " + jwtService.generateAccessToken(user);
    }

    @Test
    @DisplayName("Record quality result transitions lot to QUALITY_VERIFIED and exposes certificate")
    void testRecordQualityResultAndRetrieve() throws Exception {
        RecordQualityResultRequest request = RecordQualityResultRequest.builder()
                .qualityScore(90.5)
                .grade("GRADE_A")
                .confidence(0.95)
                .modelProvider("AGRI_VISION_AI")
                .modelVersion("v2.1")
                .attributes(Map.of("colorScore", 9.2, "defectPercentage", 0.8, "sizeUniformity", "HIGH"))
                .build();

        // 1. Record Quality Result -> 201 Created
        mockMvc.perform(post("/api/v1/lots/" + testLot.getId() + "/quality/record")
                        .header("Authorization", token(farmer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.qualityScore").value(90.5))
                .andExpect(jsonPath("$.data.grade").value("GRADE_A"))
                .andExpect(jsonPath("$.data.modelProvider").value("AGRI_VISION_AI"))
                .andExpect(jsonPath("$.data.attributes.sizeUniformity").value("HIGH"));

        // 2. Verify lot status has transitioned to QUALITY_VERIFIED in DB
        Lot updatedLot = lotRepository.findById(testLot.getId()).orElseThrow();
        assertThat(updatedLot.getStatus()).isEqualTo(LotStatus.QUALITY_VERIFIED);

        // 3. Query latest quality result
        mockMvc.perform(get("/api/v1/lots/" + testLot.getId() + "/quality")
                        .header("Authorization", token(farmer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.qualityScore").value(90.5))
                .andExpect(jsonPath("$.data.grade").value("GRADE_A"));

        // 4. Query quality history
        mockMvc.perform(get("/api/v1/lots/" + testLot.getId() + "/quality/history")
                        .header("Authorization", token(farmer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1));
    }
}
