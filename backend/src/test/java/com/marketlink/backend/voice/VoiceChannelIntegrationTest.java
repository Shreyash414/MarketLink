package com.marketlink.backend.voice;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.domain.crop.entity.Crop;
import com.marketlink.backend.domain.crop.repository.CropRepository;
import com.marketlink.backend.domain.market.entity.Market;
import com.marketlink.backend.domain.market.repository.MarketRepository;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.BidRepository;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.domain.marketprice.entity.MarketPrice;
import com.marketlink.backend.domain.marketprice.repository.MarketPriceRepository;
import com.marketlink.backend.domain.offer.entity.Offer;
import com.marketlink.backend.domain.offer.enums.OfferStatus;
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
import com.marketlink.backend.security.jwt.JwtService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class VoiceChannelIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private CropRepository cropRepository;

    @Autowired
    private MarketRepository marketRepository;

    @Autowired
    private MarketPriceRepository marketPriceRepository;

    @Autowired
    private LotRepository lotRepository;

    @Autowired
    private OfferRepository offerRepository;

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

    private User farmerA;
    private User farmerB;
    private User buyer;
    private Crop onion;
    private Market puneMarket;
    private Lot lotA;
    private Offer pendingOffer;

    @BeforeEach
    void setUp() {
        offerRepository.deleteAll();
        bidRepository.deleteAll();
        lotRepository.deleteAll();
        marketPriceRepository.deleteAll();
        cropRepository.deleteAll();
        marketRepository.deleteAll();
        farmerProfileRepository.deleteAll();
        buyerProfileRepository.deleteAll();
        userRepository.deleteAll();

        onion = cropRepository.save(Crop.builder()
                .name("ONION")
                .category("VEGETABLE")
                .unit("QUINTAL")
                .active(true)
                .build());

        puneMarket = marketRepository.save(Market.builder()
                .name("Pune APMC")
                .district("Pune")
                .state("Maharashtra")
                .active(true)
                .build());

        marketPriceRepository.save(MarketPrice.builder()
                .cropId(onion.getId())
                .marketId(puneMarket.getId())
                .priceDate(LocalDate.now())
                .minPrice(2000.0)
                .maxPrice(2800.0)
                .modalPrice(2400.0)
                .unit("QUINTAL")
                .build());

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

        buyerProfileRepository.save(BuyerProfile.builder()
                .userId(buyer.getId())
                .businessName("Agro Fresh Trading")
                .build());

        lotA = lotRepository.save(Lot.builder()
                .farmerId(farmerA.getId())
                .cropId(onion.getId())
                .cropName("ONION")
                .quantity(500.0)
                .expectedPrice(35.0)
                .status(LotStatus.PUBLISHED)
                .build());

        pendingOffer = offerRepository.save(Offer.builder()
                .lotId(lotA.getId())
                .buyerId(buyer.getId())
                .offeredPrice(34.0)
                .quantity(500.0)
                .status(OfferStatus.PENDING)
                .build());
    }

    private String token(User user) {
        return "Bearer " + jwtService.generateAccessToken(user);
    }

    @Test
    @DisplayName("Voice price query returns formatted TTS summary")
    void testVoicePriceQuery() throws Exception {
        mockMvc.perform(get("/api/v1/voice/prices")
                        .param("cropName", "ONION")
                        .param("marketName", "Pune APMC"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.modalPrice").value(2400.0))
                .andExpect(jsonPath("$.data.voiceSummary").isString());
    }

    @Test
    @DisplayName("Farmer retrieves pending voice offers and accepts via voice confirmation")
    void testVoiceOfferInquiryAndAcceptance() throws Exception {
        // 1. Inquire offers
        mockMvc.perform(get("/api/v1/voice/offers")
                        .header("Authorization", token(farmerA)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].offeredPrice").value(34.0));

        // 2. Accept offer via voice
        mockMvc.perform(post("/api/v1/voice/offers/" + pendingOffer.getId() + "/accept")
                        .header("Authorization", token(farmerA)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true));

        Offer updated = offerRepository.findById(pendingOffer.getId()).orElseThrow();
        assertThat(updated.getStatus()).isEqualTo(OfferStatus.ACCEPTED);
    }

    @Test
    @DisplayName("Farmer B cannot accept Farmer A's offer over voice (403 Forbidden)")
    void testFarmerCannotAcceptOtherFarmerOffer() throws Exception {
        mockMvc.perform(post("/api/v1/voice/offers/" + pendingOffer.getId() + "/accept")
                        .header("Authorization", token(farmerB)))
                .andExpect(status().isForbidden());
    }
}
