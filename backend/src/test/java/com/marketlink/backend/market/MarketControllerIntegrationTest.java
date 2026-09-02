package com.marketlink.backend.market;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.domain.market.entity.Market;
import com.marketlink.backend.domain.market.repository.MarketRepository;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.AccountStatus;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.enums.VerificationState;
import com.marketlink.backend.domain.user.repository.UserRepository;
import com.marketlink.backend.market.dto.CreateMarketRequest;
import com.marketlink.backend.market.dto.UpdateMarketRequest;
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
class MarketControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private MarketRepository marketRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private ObjectMapper objectMapper;

    private String authToken;
    private User testUser;

    @BeforeEach
    void setUp() {
        marketRepository.deleteAll();
        userRepository.deleteAll();

        testUser = userRepository.save(User.builder()
                .phoneNumber("9876543210")
                .passwordHash("hashedPass")
                .role(Role.FARMER)
                .verificationState(VerificationState.VERIFIED)
                .accountStatus(AccountStatus.ACTIVE)
                .build());

        authToken = jwtService.generateAccessToken(testUser);
    }

    @Test
    @DisplayName("GET /api/v1/markets returns active markets")
    void testGetAllMarkets() throws Exception {
        marketRepository.save(Market.builder()
                .name("Pune APMC")
                .district("Pune")
                .state("Maharashtra")
                .latitude(18.5204)
                .longitude(73.8567)
                .active(true)
                .build());

        marketRepository.save(Market.builder()
                .name("Nashik APMC")
                .district("Nashik")
                .state("Maharashtra")
                .latitude(19.9975)
                .longitude(73.7898)
                .active(true)
                .build());

        mockMvc.perform(get("/api/v1/markets")
                        .header("Authorization", "Bearer " + authToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.length()").value(2));
    }

    @Test
    @DisplayName("GET /api/v1/markets?state=Maharashtra&district=Pune filters by region")
    void testGetAllMarkets_Filtered() throws Exception {
        marketRepository.save(Market.builder()
                .name("Pune APMC")
                .district("Pune")
                .state("Maharashtra")
                .active(true)
                .build());

        marketRepository.save(Market.builder()
                .name("Azadpur Mandi")
                .district("North Delhi")
                .state("Delhi")
                .active(true)
                .build());

        mockMvc.perform(get("/api/v1/markets")
                        .param("state", "Maharashtra")
                        .param("district", "Pune")
                        .header("Authorization", "Bearer " + authToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].name").value("Pune APMC"));
    }

    @Test
    @DisplayName("POST /api/v1/markets creates new market record")
    void testCreateMarket_Success() throws Exception {
        CreateMarketRequest request = CreateMarketRequest.builder()
                .name("Baramati Mandi")
                .district("Pune")
                .state("Maharashtra")
                .latitude(18.1517)
                .longitude(74.5771)
                .build();

        mockMvc.perform(post("/api/v1/markets")
                        .header("Authorization", "Bearer " + authToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.name").value("Baramati Mandi"))
                .andExpect(jsonPath("$.data.district").value("Pune"))
                .andExpect(jsonPath("$.data.state").value("Maharashtra"));

        assertThat(marketRepository.existsByNameIgnoreCaseAndDistrictIgnoreCaseAndStateIgnoreCase(
                "Baramati Mandi", "Pune", "Maharashtra")).isTrue();
    }

    @Test
    @DisplayName("POST /api/v1/markets returns 400 when required fields are missing")
    void testCreateMarket_ValidationError() throws Exception {
        CreateMarketRequest invalidRequest = CreateMarketRequest.builder()
                .name("")
                .district("")
                .state("")
                .build();

        mockMvc.perform(post("/api/v1/markets")
                        .header("Authorization", "Bearer " + authToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(invalidRequest)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.success").value(false));
    }

    @Test
    @DisplayName("POST /api/v1/markets returns 409 Conflict when duplicate market exists")
    void testCreateMarket_DuplicateConflict() throws Exception {
        marketRepository.save(Market.builder()
                .name("Pune APMC")
                .district("Pune")
                .state("Maharashtra")
                .active(true)
                .build());

        CreateMarketRequest duplicateReq = CreateMarketRequest.builder()
                .name("Pune APMC")
                .district("Pune")
                .state("Maharashtra")
                .build();

        mockMvc.perform(post("/api/v1/markets")
                        .header("Authorization", "Bearer " + authToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(duplicateReq)))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.success").value(false));
    }

    @Test
    @DisplayName("GET /api/v1/markets/{id} returns market details or 404")
    void testGetMarketById() throws Exception {
        Market saved = marketRepository.save(Market.builder()
                .name("Lasalgaon APMC")
                .district("Nashik")
                .state("Maharashtra")
                .active(true)
                .build());

        mockMvc.perform(get("/api/v1/markets/" + saved.getId())
                        .header("Authorization", "Bearer " + authToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.name").value("Lasalgaon APMC"));

        mockMvc.perform(get("/api/v1/markets/" + UUID.randomUUID())
                        .header("Authorization", "Bearer " + authToken))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("PUT /api/v1/markets/{id} updates market details")
    void testUpdateMarket() throws Exception {
        Market saved = marketRepository.save(Market.builder()
                .name("Vashi APMC")
                .district("Thane")
                .state("Maharashtra")
                .active(true)
                .build());

        UpdateMarketRequest updateReq = UpdateMarketRequest.builder()
                .name("Navi Mumbai Vashi APMC")
                .latitude(19.0760)
                .build();

        mockMvc.perform(put("/api/v1/markets/" + saved.getId())
                        .header("Authorization", "Bearer " + authToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updateReq)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.name").value("Navi Mumbai Vashi APMC"));
    }

    @Test
    @DisplayName("DELETE /api/v1/markets/{id} deletes market record")
    void testDeleteMarket() throws Exception {
        Market saved = marketRepository.save(Market.builder()
                .name("Kalyan APMC")
                .district("Thane")
                .state("Maharashtra")
                .active(true)
                .build());

        mockMvc.perform(delete("/api/v1/markets/" + saved.getId())
                        .header("Authorization", "Bearer " + authToken))
                .andExpect(status().isOk());

        assertThat(marketRepository.findById(saved.getId())).isEmpty();
    }
}
