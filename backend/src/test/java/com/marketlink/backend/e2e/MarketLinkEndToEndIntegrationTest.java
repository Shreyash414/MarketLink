package com.marketlink.backend.e2e;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.ai.dto.RecordQualityResultRequest;
import com.marketlink.backend.crop.dto.CreateCropRequest;
import com.marketlink.backend.domain.crop.repository.CropRepository;
import com.marketlink.backend.domain.image.repository.LotImageRepository;
import com.marketlink.backend.domain.market.repository.MarketRepository;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.BidRepository;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.domain.marketprice.repository.MarketPriceRepository;
import com.marketlink.backend.domain.offer.enums.OfferStatus;
import com.marketlink.backend.domain.offer.repository.OfferRepository;
import com.marketlink.backend.domain.quality.repository.QualityAnalysisResultRepository;
import com.marketlink.backend.domain.user.entity.BuyerProfile;
import com.marketlink.backend.domain.user.entity.FarmerProfile;
import com.marketlink.backend.domain.user.entity.User;
import com.marketlink.backend.domain.user.enums.AccountStatus;
import com.marketlink.backend.domain.user.enums.Role;
import com.marketlink.backend.domain.user.enums.VerificationState;
import com.marketlink.backend.domain.user.repository.BuyerProfileRepository;
import com.marketlink.backend.domain.user.repository.FarmerProfileRepository;
import com.marketlink.backend.domain.user.repository.UserRepository;
import com.marketlink.backend.lot.dto.CreateLotRequest;
import com.marketlink.backend.market.dto.CreateMarketRequest;
import com.marketlink.backend.marketprice.dto.RecordMarketPriceRequest;
import com.marketlink.backend.offer.dto.CreateOfferRequest;
import com.marketlink.backend.security.jwt.JwtService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.time.LocalDate;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class MarketLinkEndToEndIntegrationTest {

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
    private LotImageRepository lotImageRepository;

    @Autowired
    private QualityAnalysisResultRepository qualityRepository;

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

    @Autowired
    private ObjectMapper objectMapper;

    private User farmerUser;
    private User buyerUser1;
    private User buyerUser2;

    @BeforeEach
    void setUp() {
        offerRepository.deleteAll();
        bidRepository.deleteAll();
        qualityRepository.deleteAll();
        lotImageRepository.deleteAll();
        lotRepository.deleteAll();
        marketPriceRepository.deleteAll();
        cropRepository.deleteAll();
        marketRepository.deleteAll();
        farmerProfileRepository.deleteAll();
        buyerProfileRepository.deleteAll();
        userRepository.deleteAll();

        // 1. Farmer user
        farmerUser = userRepository.save(User.builder()
                .phoneNumber("9876543210")
                .passwordHash("passHash")
                .role(Role.FARMER)
                .verificationState(VerificationState.VERIFIED)
                .accountStatus(AccountStatus.ACTIVE)
                .build());

        farmerProfileRepository.save(FarmerProfile.builder()
                .userId(farmerUser.getId())
                .fullName("Ramesh Kisan")
                .district("Pune")
                .state("Maharashtra")
                .build());

        // 2. Buyer 1 user
        buyerUser1 = userRepository.save(User.builder()
                .phoneNumber("9876543221")
                .passwordHash("passHash")
                .role(Role.BUYER)
                .verificationState(VerificationState.VERIFIED)
                .accountStatus(AccountStatus.ACTIVE)
                .build());

        buyerProfileRepository.save(BuyerProfile.builder()
                .userId(buyerUser1.getId())
                .businessName("Mahalaxmi Agro Wholesale")
                .gstin("27AAAAA1111A1Z1")
                .build());

        // 3. Buyer 2 user
        buyerUser2 = userRepository.save(User.builder()
                .phoneNumber("9876543222")
                .passwordHash("passHash")
                .role(Role.BUYER)
                .verificationState(VerificationState.VERIFIED)
                .accountStatus(AccountStatus.ACTIVE)
                .build());

        buyerProfileRepository.save(BuyerProfile.builder()
                .userId(buyerUser2.getId())
                .businessName("Sahyadri Fresh Traders")
                .gstin("27BBBBB2222B2Z2")
                .build());
    }

    private String token(User user) {
        return "Bearer " + jwtService.generateAccessToken(user);
    }

    private byte[] createDummyProduceImage() throws IOException {
        BufferedImage image = new BufferedImage(1200, 900, BufferedImage.TYPE_INT_RGB);
        Graphics2D g2d = image.createGraphics();
        g2d.setColor(Color.ORANGE);
        g2d.fillRect(0, 0, 1200, 900);
        g2d.setColor(Color.BLACK);
        g2d.drawString("Fresh Produce Onion", 50, 50);
        g2d.dispose();

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(image, "jpg", baos);
        return baos.toByteArray();
    }

    @Test
    @DisplayName("Complete Phase 2 End-to-End Workflow: Master Data -> Lot Creation -> Image Upload -> AI Grading -> Publishing -> Multi-Buyer Offers -> Voice Acceptance")
    void testCompleteEndToEndMarketplaceWorkflow() throws Exception {

        // ==========================================
        // 1. Master Data Setup: Crop & Market
        // ==========================================
        CreateCropRequest cropReq = CreateCropRequest.builder()
                .name("NASHIK RED ONION")
                .category("VEGETABLE")
                .unit("QUINTAL")
                .build();

        String cropRespStr = mockMvc.perform(post("/api/v1/crops")
                        .header("Authorization", token(farmerUser))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(cropReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.name").value("NASHIK RED ONION"))
                .andReturn().getResponse().getContentAsString();

        UUID cropId = UUID.fromString(objectMapper.readTree(cropRespStr).path("data").path("id").asText());

        CreateMarketRequest marketReq = CreateMarketRequest.builder()
                .name("Pune Gultekdi APMC")
                .district("Pune")
                .state("Maharashtra")
                .latitude(18.4984)
                .longitude(73.8672)
                .build();

        String marketRespStr = mockMvc.perform(post("/api/v1/markets")
                        .header("Authorization", token(farmerUser))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(marketReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.name").value("Pune Gultekdi APMC"))
                .andReturn().getResponse().getContentAsString();

        UUID marketId = UUID.fromString(objectMapper.readTree(marketRespStr).path("data").path("id").asText());

        // ==========================================
        // 2. Baseline Mandi Price Recording
        // ==========================================
        RecordMarketPriceRequest priceReq = RecordMarketPriceRequest.builder()
                .cropId(cropId)
                .marketId(marketId)
                .priceDate(LocalDate.now())
                .minPrice(2200.0)
                .maxPrice(3200.0)
                .modalPrice(2700.0)
                .arrivalQuantity(800.0)
                .unit("QUINTAL")
                .source("APMC_AGMARKNET")
                .build();

        mockMvc.perform(post("/api/v1/market-prices")
                        .header("Authorization", token(farmerUser))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(priceReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.modalPrice").value(2700.0));

        // ==========================================
        // 3. Farmer creates produce lot in DRAFT
        // ==========================================
        CreateLotRequest lotReq = CreateLotRequest.builder()
                .cropId(cropId)
                .marketId(marketId)
                .variety("Garva Red")
                .quantity(1000.0)
                .unit("KG")
                .harvestDate(LocalDate.now().minusDays(2))
                .expectedPrice(35.0)
                .minimumAcceptablePrice(30.0)
                .location("Khed, Pune")
                .build();

        String lotRespStr = mockMvc.perform(post("/api/v1/lots")
                        .header("Authorization", token(farmerUser))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(lotReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.status").value("DRAFT"))
                .andExpect(jsonPath("$.data.cropName").value("NASHIK RED ONION"))
                .andReturn().getResponse().getContentAsString();

        UUID lotId = UUID.fromString(objectMapper.readTree(lotRespStr).path("data").path("id").asText());

        // ==========================================
        // 4. Farmer uploads and compresses produce photograph
        // ==========================================
        byte[] imgBytes = createDummyProduceImage();
        MockMultipartFile photoFile = new MockMultipartFile(
                "file", "harvest_batch.jpg", "image/jpeg", imgBytes);

        String imgRespStr = mockMvc.perform(multipart("/api/v1/lots/" + lotId + "/images")
                        .file(photoFile)
                        .param("imageType", "PRODUCE_PHOTO")
                        .header("Authorization", token(farmerUser)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.contentType").value("image/jpeg"))
                .andExpect(jsonPath("$.data.downloadUrl").isString())
                .andReturn().getResponse().getContentAsString();

        UUID imageId = UUID.fromString(objectMapper.readTree(imgRespStr).path("data").path("id").asText());

        // Verify direct binary image streaming endpoint
        mockMvc.perform(get("/api/v1/lots/" + lotId + "/images/" + imageId)
                        .header("Authorization", token(buyerUser1)))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Type", "image/jpeg"));

        // ==========================================
        // 5. AI Grading Service records Quality Analysis Result
        // ==========================================
        RecordQualityResultRequest qualityReq = RecordQualityResultRequest.builder()
                .qualityScore(94.0)
                .grade("GRADE_A_PREMIUM")
                .confidence(0.97)
                .modelProvider("AGRI_VISION_DEEP_GRADER")
                .modelVersion("v3.0.1")
                .attributes(Map.of("uniformity", "96%", "defectRate", 0.5, "firmness", "HIGH"))
                .build();

        mockMvc.perform(post("/api/v1/lots/" + lotId + "/quality/record")
                        .header("Authorization", token(farmerUser))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(qualityReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.grade").value("GRADE_A_PREMIUM"))
                .andExpect(jsonPath("$.data.qualityScore").value(94.0));

        // Verify lot transitioned to QUALITY_VERIFIED
        assertThat(lotRepository.findById(lotId).orElseThrow().getStatus())
                .isEqualTo(LotStatus.QUALITY_VERIFIED);

        // ==========================================
        // 6. Farmer publishes the quality-verified lot
        // ==========================================
        mockMvc.perform(post("/api/v1/lots/" + lotId + "/publish")
                        .header("Authorization", token(farmerUser)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("PUBLISHED"));

        // ==========================================
        // 7. Buyer browses published lots & views quality
        // ==========================================
        mockMvc.perform(get("/api/v1/lots")
                        .param("cropId", cropId.toString())
                        .header("Authorization", token(buyerUser1)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].id").value(lotId.toString()));

        mockMvc.perform(get("/api/v1/lots/" + lotId + "/quality")
                        .header("Authorization", token(buyerUser1)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.grade").value("GRADE_A_PREMIUM"));

        // ==========================================
        // 8. Buyer 1 submits purchase offer of ₹34/kg
        // ==========================================
        CreateOfferRequest offerReq1 = CreateOfferRequest.builder()
                .offeredPrice(34.0)
                .quantity(1000.0)
                .notes("Pickup with dedicated truck in 24 hours")
                .build();

        String offer1RespStr = mockMvc.perform(post("/api/v1/lots/" + lotId + "/offers")
                        .header("Authorization", token(buyerUser1))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(offerReq1)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.status").value("PENDING"))
                .andExpect(jsonPath("$.data.offeredPrice").value(34.0))
                .andReturn().getResponse().getContentAsString();

        UUID offer1Id = UUID.fromString(objectMapper.readTree(offer1RespStr).path("data").path("id").asText());

        // Lot transitions to OFFER_RECEIVED
        assertThat(lotRepository.findById(lotId).orElseThrow().getStatus())
                .isEqualTo(LotStatus.OFFER_RECEIVED);

        // ==========================================
        // 9. Buyer 2 submits competing offer of ₹32/kg
        // ==========================================
        CreateOfferRequest offerReq2 = CreateOfferRequest.builder()
                .offeredPrice(32.0)
                .quantity(1000.0)
                .notes("Standard delivery terms")
                .build();

        String offer2RespStr = mockMvc.perform(post("/api/v1/lots/" + lotId + "/offers")
                        .header("Authorization", token(buyerUser2))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(offerReq2)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.status").value("PENDING"))
                .andExpect(jsonPath("$.data.offeredPrice").value(32.0))
                .andReturn().getResponse().getContentAsString();

        UUID offer2Id = UUID.fromString(objectMapper.readTree(offer2RespStr).path("data").path("id").asText());

        // ==========================================
        // 10. Voice Channel: Farmer checks pending offers and accepts Offer 1
        // ==========================================
        mockMvc.perform(get("/api/v1/voice/offers")
                        .header("Authorization", token(farmerUser)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(2))
                .andExpect(jsonPath("$.data[0].voiceSummary").isString());

        // Farmer confirms acceptance of Buyer 1's offer via voice/API
        mockMvc.perform(post("/api/v1/voice/offers/" + offer1Id + "/accept")
                        .header("Authorization", token(farmerUser)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true));

        // ==========================================
        // 11. Verification of Post-Acceptance State
        // ==========================================
        // Offer 1 is ACCEPTED
        assertThat(offerRepository.findById(offer1Id).orElseThrow().getStatus())
                .isEqualTo(OfferStatus.ACCEPTED);

        // Lot is ACCEPTED
        assertThat(lotRepository.findById(lotId).orElseThrow().getStatus())
                .isEqualTo(LotStatus.ACCEPTED);

        // Competing Offer 2 is automatically REJECTED
        assertThat(offerRepository.findById(offer2Id).orElseThrow().getStatus())
                .isEqualTo(OfferStatus.REJECTED);
    }
}
