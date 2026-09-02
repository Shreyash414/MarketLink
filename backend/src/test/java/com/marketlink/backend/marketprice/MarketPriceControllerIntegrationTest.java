package com.marketlink.backend.marketprice;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.domain.crop.entity.Crop;
import com.marketlink.backend.domain.crop.repository.CropRepository;
import com.marketlink.backend.domain.market.entity.Market;
import com.marketlink.backend.domain.market.repository.MarketRepository;
import com.marketlink.backend.domain.marketprice.entity.MarketPrice;
import com.marketlink.backend.domain.marketprice.repository.MarketPriceRepository;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.AccountStatus;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.enums.VerificationState;
import com.marketlink.backend.domain.user.repository.UserRepository;
import com.marketlink.backend.marketprice.dto.RecordMarketPriceRequest;
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

import java.time.LocalDate;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class MarketPriceControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private MarketPriceRepository marketPriceRepository;

    @Autowired
    private CropRepository cropRepository;

    @Autowired
    private MarketRepository marketRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private ObjectMapper objectMapper;

    private User adminUser;
    private Crop onionCrop;
    private Market puneMarket;

    @BeforeEach
    void setUp() {
        marketPriceRepository.deleteAll();
        cropRepository.deleteAll();
        marketRepository.deleteAll();
        userRepository.deleteAll();

        adminUser = userRepository.save(User.builder()
                .phoneNumber("9876543210")
                .passwordHash("passHash")
                .role(Role.FARMER)
                .verificationState(VerificationState.VERIFIED)
                .accountStatus(AccountStatus.ACTIVE)
                .build());

        onionCrop = cropRepository.save(Crop.builder()
                .name("ONION")
                .category("VEGETABLE")
                .unit("QUINTAL")
                .active(true)
                .build());

        puneMarket = marketRepository.save(Market.builder()
                .name("Pune APMC")
                .district("Pune")
                .state("Maharashtra")
                .latitude(18.5204)
                .longitude(73.8567)
                .active(true)
                .build());
    }

    private String token(User user) {
        return "Bearer " + jwtService.generateAccessToken(user);
    }

    @Test
    @DisplayName("Record market price and query via filters and latest endpoint")
    void testRecordAndQueryMarketPrice() throws Exception {
        RecordMarketPriceRequest request = RecordMarketPriceRequest.builder()
                .cropId(onionCrop.getId())
                .marketId(puneMarket.getId())
                .priceDate(LocalDate.now())
                .minPrice(2000.0)
                .maxPrice(2800.0)
                .modalPrice(2400.0)
                .arrivalQuantity(500.0)
                .unit("QUINTAL")
                .source("APMC_AGMARKNET")
                .build();

        // 1. Record market price -> 201 Created
        String respStr = mockMvc.perform(post("/api/v1/market-prices")
                        .header("Authorization", token(adminUser))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.cropName").value("ONION"))
                .andExpect(jsonPath("$.data.marketName").value("Pune APMC"))
                .andExpect(jsonPath("$.data.modalPrice").value(2400.0))
                .andReturn().getResponse().getContentAsString();

        String priceIdStr = objectMapper.readTree(respStr).path("data").path("id").asText();

        // 2. Query market prices by cropId
        mockMvc.perform(get("/api/v1/market-prices")
                        .param("cropId", onionCrop.getId().toString())
                        .header("Authorization", token(adminUser)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].id").value(priceIdStr));

        // 3. Query latest market price
        mockMvc.perform(get("/api/v1/market-prices/latest")
                        .param("cropId", onionCrop.getId().toString())
                        .param("marketId", puneMarket.getId().toString())
                        .header("Authorization", token(adminUser)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.modalPrice").value(2400.0));

        // 4. Query price by ID
        mockMvc.perform(get("/api/v1/market-prices/" + priceIdStr)
                        .header("Authorization", token(adminUser)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.cropName").value("ONION"));
    }

    @Test
    @DisplayName("Validation failure on recording price with minPrice > maxPrice")
    void testRecordPriceValidationFailure() throws Exception {
        RecordMarketPriceRequest invalidRequest = RecordMarketPriceRequest.builder()
                .cropId(onionCrop.getId())
                .marketId(puneMarket.getId())
                .priceDate(LocalDate.now())
                .minPrice(3000.0)
                .maxPrice(2000.0)
                .modalPrice(2500.0)
                .build();

        mockMvc.perform(post("/api/v1/market-prices")
                        .header("Authorization", token(adminUser))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(invalidRequest)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.success").value(false));
    }
}
