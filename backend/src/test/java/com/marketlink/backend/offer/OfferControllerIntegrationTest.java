package com.marketlink.backend.offer;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.BidRepository;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.domain.offer.repository.OfferRepository;
import com.marketlink.backend.domain.user.entity.BuyerProfile;
import com.marketlink.backend.domain.user.entity.FarmerProfile;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.AccountStatus;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.enums.VerificationState;
import com.marketlink.backend.domain.user.repository.BuyerProfileRepository;
import com.marketlink.backend.domain.user.repository.FarmerProfileRepository;
import com.marketlink.backend.domain.user.repository.UserRepository;
import com.marketlink.backend.offer.dto.CreateOfferRequest;
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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class OfferControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private OfferRepository offerRepository;

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
    private User buyer;
    private Lot publishedLot;

    @BeforeEach
    void setUp() {
        offerRepository.deleteAll();
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

        buyer = userRepository.save(User.builder()
                .phoneNumber("9876543220")
                .passwordHash("passHash")
                .role(Role.BUYER)
                .verificationState(VerificationState.VERIFIED)
                .accountStatus(AccountStatus.ACTIVE)
                .build());

        buyerProfileRepository.save(BuyerProfile.builder()
                .userId(buyer.getId())
                .businessName("Agro Fresh Trading")
                .gstin("27AAAAA0000A1Z5")
                .build());

        publishedLot = lotRepository.save(Lot.builder()
                .farmerId(farmer.getId())
                .cropName("ONION")
                .quantity(500.0)
                .expectedPrice(35.0)
                .minimumAcceptablePrice(30.0)
                .status(LotStatus.PUBLISHED)
                .build());
    }

    private String token(User user) {
        return "Bearer " + jwtService.generateAccessToken(user);
    }

    @Test
    @DisplayName("Buyer places offer, queries buyer offers, and farmer accepts offer")
    void testOfferLifecycleFlow() throws Exception {
        CreateOfferRequest request = CreateOfferRequest.builder()
                .offeredPrice(34.0)
                .quantity(500.0)
                .notes("Delivery within 3 days")
                .build();

        // 1. Buyer places offer -> 201 Created
        String offerRespStr = mockMvc.perform(post("/api/v1/lots/" + publishedLot.getId() + "/offers")
                        .header("Authorization", token(buyer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.offeredPrice").value(34.0))
                .andExpect(jsonPath("$.data.status").value("PENDING"))
                .andReturn().getResponse().getContentAsString();

        String offerIdStr = objectMapper.readTree(offerRespStr).path("data").path("id").asText();
        UUID offerId = UUID.fromString(offerIdStr);

        // Verify lot status changed to OFFER_RECEIVED
        Lot updatedLot = lotRepository.findById(publishedLot.getId()).orElseThrow();
        assertThat(updatedLot.getStatus()).isEqualTo(LotStatus.OFFER_RECEIVED);

        // 2. Buyer views my offers
        mockMvc.perform(get("/api/v1/buyers/me/offers")
                        .header("Authorization", token(buyer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].id").value(offerIdStr));

        // 3. Farmer views offers on lot
        mockMvc.perform(get("/api/v1/lots/" + publishedLot.getId() + "/offers")
                        .header("Authorization", token(farmer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1));

        // 4. Farmer accepts offer -> 200 OK
        mockMvc.perform(post("/api/v1/offers/" + offerId + "/accept")
                        .header("Authorization", token(farmer)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.status").value("ACCEPTED"));

        // Verify lot status changed to ACCEPTED
        Lot finalLot = lotRepository.findById(publishedLot.getId()).orElseThrow();
        assertThat(finalLot.getStatus()).isEqualTo(LotStatus.ACCEPTED);
    }

    @Test
    @DisplayName("Farmer cannot place offer on own lot (403/400)")
    void testFarmerCannotOfferOnOwnLot() throws Exception {
        CreateOfferRequest request = CreateOfferRequest.builder()
                .offeredPrice(34.0)
                .quantity(500.0)
                .build();

        mockMvc.perform(post("/api/v1/lots/" + publishedLot.getId() + "/offers")
                        .header("Authorization", token(farmer))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isForbidden());
    }
}
