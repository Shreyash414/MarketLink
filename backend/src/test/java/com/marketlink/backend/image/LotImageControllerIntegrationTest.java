package com.marketlink.backend.image;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.domain.image.entity.LotImage;
import com.marketlink.backend.domain.image.repository.LotImageRepository;
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
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class LotImageControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private LotImageRepository lotImageRepository;

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

    private User farmerA;
    private User farmerB;
    private User buyer;
    private Lot lotA;

    @BeforeEach
    void setUp() {
        lotImageRepository.deleteAll();
        bidRepository.deleteAll();
        lotRepository.deleteAll();
        farmerProfileRepository.deleteAll();
        buyerProfileRepository.deleteAll();
        userRepository.deleteAll();

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

        lotA = lotRepository.save(Lot.builder()
                .farmerId(farmerA.getId())
                .cropName("ONION")
                .quantity(500.0)
                .expectedPrice(30.0)
                .status(LotStatus.DRAFT)
                .build());
    }

    private String token(User user) {
        return "Bearer " + jwtService.generateAccessToken(user);
    }

    private byte[] createTestImageBytes(int width, int height) throws IOException {
        BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        Graphics2D g2d = image.createGraphics();
        g2d.setColor(Color.GREEN);
        g2d.fillRect(0, 0, width, height);
        g2d.dispose();

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(image, "jpg", baos);
        return baos.toByteArray();
    }

    @Test
    @DisplayName("Farmer uploads lot photo, retrieves metadata, streams binary JPEG, and deletes it")
    void testUploadRetrieveStreamAndDeleteImage() throws Exception {
        byte[] imgBytes = createTestImageBytes(1000, 750);
        MockMultipartFile file = new MockMultipartFile(
                "file", "onion.jpg", "image/jpeg", imgBytes);

        // 1. Upload photo -> 201 Created
        String uploadRespStr = mockMvc.perform(multipart("/api/v1/lots/" + lotA.getId() + "/images")
                        .file(file)
                        .param("imageType", "PRODUCE_PHOTO")
                        .header("Authorization", token(farmerA)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.contentType").value("image/jpeg"))
                .andExpect(jsonPath("$.data.originalFilename").value("onion.jpg"))
                .andExpect(jsonPath("$.data.downloadUrl").isString())
                .andReturn().getResponse().getContentAsString();

        String imageIdStr = objectMapper.readTree(uploadRespStr).path("data").path("id").asText();
        UUID imageId = UUID.fromString(imageIdStr);

        // 2. Query lot image metadata list
        mockMvc.perform(get("/api/v1/lots/" + lotA.getId() + "/images")
                        .header("Authorization", token(farmerA)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].id").value(imageIdStr));

        // 3. Direct raw binary JPEG stream
        mockMvc.perform(get("/api/v1/lots/" + lotA.getId() + "/images/" + imageId)
                        .header("Authorization", token(buyer)))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Type", "image/jpeg"))
                .andExpect(header().string("Cache-Control", "private, max-age=3600"))
                .andExpect(content().bytes(lotImageRepository.findById(imageId).orElseThrow().getImageData().getData()));

        // 4. Delete photo
        mockMvc.perform(delete("/api/v1/lots/" + lotA.getId() + "/images/" + imageId)
                        .header("Authorization", token(farmerA)))
                .andExpect(status().isOk());

        assertThat(lotImageRepository.findById(imageId)).isEmpty();
    }

    @Test
    @DisplayName("Farmer cannot upload photo to another farmer's lot (403 Forbidden)")
    void testFarmerCannotUploadToAnotherFarmerLot() throws Exception {
        byte[] imgBytes = createTestImageBytes(400, 300);
        MockMultipartFile file = new MockMultipartFile(
                "file", "onion.jpg", "image/jpeg", imgBytes);

        mockMvc.perform(multipart("/api/v1/lots/" + lotA.getId() + "/images")
                        .file(file)
                        .header("Authorization", token(farmerB)))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("Buyer cannot upload photo to a lot (403 Forbidden)")
    void testBuyerCannotUploadImage() throws Exception {
        byte[] imgBytes = createTestImageBytes(400, 300);
        MockMultipartFile file = new MockMultipartFile(
                "file", "onion.jpg", "image/jpeg", imgBytes);

        mockMvc.perform(multipart("/api/v1/lots/" + lotA.getId() + "/images")
                        .file(file)
                        .header("Authorization", token(buyer)))
                .andExpect(status().isForbidden());
    }
}
