package com.marketlink.backend.crop;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.crop.dto.CreateCropRequest;
import com.marketlink.backend.crop.dto.UpdateCropRequest;
import com.marketlink.backend.domain.crop.entity.Crop;
import com.marketlink.backend.domain.crop.repository.CropRepository;
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
class CropControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private CropRepository cropRepository;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private com.marketlink.backend.domain.user.repository.UserRepository userRepository;

    private String authToken;
    private com.marketlink.backend.domain.user.entity.User testUser;

    @BeforeEach
    void setUp() {
        cropRepository.deleteAll();
        userRepository.deleteAll();

        testUser = userRepository.save(com.marketlink.backend.domain.user.entity.User.builder()
                .phoneNumber("9876543210")
                .passwordHash("hashedPass")
                .role(com.marketlink.backend.domain.user.enums.Role.FARMER)
                .verificationState(com.marketlink.backend.domain.user.enums.VerificationState.VERIFIED)
                .accountStatus(com.marketlink.backend.domain.user.enums.AccountStatus.ACTIVE)
                .build());

        authToken = jwtService.generateAccessToken(testUser);
    }

    @Test
    @DisplayName("GET /api/v1/crops returns active crops")
    void testGetAllCrops() throws Exception {
        Crop onion = cropRepository.save(Crop.builder()
                .name("ONION")
                .category("VEGETABLE")
                .unit("KG")
                .active(true)
                .build());

        Crop wheat = cropRepository.save(Crop.builder()
                .name("WHEAT")
                .category("GRAIN")
                .unit("QUINTAL")
                .active(true)
                .build());

        mockMvc.perform(get("/api/v1/crops")
                        .header("Authorization", "Bearer " + authToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.length()").value(2))
                .andExpect(jsonPath("$.data[0].name").value("ONION"))
                .andExpect(jsonPath("$.data[1].name").value("WHEAT"));
    }

    @Test
    @DisplayName("GET /api/v1/crops?category=VEGETABLE filters by category")
    void testGetAllCrops_CategoryFilter() throws Exception {
        cropRepository.save(Crop.builder()
                .name("ONION")
                .category("VEGETABLE")
                .unit("KG")
                .active(true)
                .build());

        cropRepository.save(Crop.builder()
                .name("WHEAT")
                .category("GRAIN")
                .unit("QUINTAL")
                .active(true)
                .build());

        mockMvc.perform(get("/api/v1/crops")
                        .param("category", "VEGETABLE")
                        .header("Authorization", "Bearer " + authToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].name").value("ONION"));
    }

    @Test
    @DisplayName("POST /api/v1/crops creates new crop master record")
    void testCreateCrop_Success() throws Exception {
        CreateCropRequest request = CreateCropRequest.builder()
                .name("Potato")
                .category("Vegetable")
                .unit("kg")
                .build();

        mockMvc.perform(post("/api/v1/crops")
                        .header("Authorization", "Bearer " + authToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.name").value("POTATO"))
                .andExpect(jsonPath("$.data.category").value("VEGETABLE"))
                .andExpect(jsonPath("$.data.unit").value("KG"))
                .andExpect(jsonPath("$.data.active").value(true));

        assertThat(cropRepository.existsByNameIgnoreCase("POTATO")).isTrue();
    }

    @Test
    @DisplayName("POST /api/v1/crops returns 400 when validation fails")
    void testCreateCrop_ValidationError() throws Exception {
        CreateCropRequest invalidRequest = CreateCropRequest.builder()
                .name("")
                .category("")
                .unit("")
                .build();

        mockMvc.perform(post("/api/v1/crops")
                        .header("Authorization", "Bearer " + authToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(invalidRequest)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error").value("Bad Request"));
    }

    @Test
    @DisplayName("POST /api/v1/crops returns 409 Conflict when duplicate name exists")
    void testCreateCrop_DuplicateConflict() throws Exception {
        cropRepository.save(Crop.builder()
                .name("ONION")
                .category("VEGETABLE")
                .unit("KG")
                .active(true)
                .build());

        CreateCropRequest duplicateRequest = CreateCropRequest.builder()
                .name("Onion")
                .category("Vegetable")
                .unit("kg")
                .build();

        mockMvc.perform(post("/api/v1/crops")
                        .header("Authorization", "Bearer " + authToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(duplicateRequest)))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.message").value("Crop with name 'ONION' already exists"));
    }

    @Test
    @DisplayName("GET /api/v1/crops/{id} returns crop or 404")
    void testGetCropById() throws Exception {
        Crop saved = cropRepository.save(Crop.builder()
                .name("TOMATO")
                .category("VEGETABLE")
                .unit("KG")
                .active(true)
                .build());

        mockMvc.perform(get("/api/v1/crops/" + saved.getId())
                        .header("Authorization", "Bearer " + authToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.name").value("TOMATO"));

        mockMvc.perform(get("/api/v1/crops/" + UUID.randomUUID())
                        .header("Authorization", "Bearer " + authToken))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("PUT /api/v1/crops/{id} updates crop")
    void testUpdateCrop() throws Exception {
        Crop saved = cropRepository.save(Crop.builder()
                .name("RICE")
                .category("GRAIN")
                .unit("KG")
                .active(true)
                .build());

        UpdateCropRequest updateRequest = UpdateCropRequest.builder()
                .name("Basmati Rice")
                .unit("Quintal")
                .build();

        mockMvc.perform(put("/api/v1/crops/" + saved.getId())
                        .header("Authorization", "Bearer " + authToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updateRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.name").value("BASMATI RICE"))
                .andExpect(jsonPath("$.data.unit").value("QUINTAL"));
    }

    @Test
    @DisplayName("DELETE /api/v1/crops/{id} deletes crop record")
    void testDeleteCrop() throws Exception {
        Crop saved = cropRepository.save(Crop.builder()
                .name("BARLEY")
                .category("GRAIN")
                .unit("KG")
                .active(true)
                .build());

        mockMvc.perform(delete("/api/v1/crops/" + saved.getId())
                        .header("Authorization", "Bearer " + authToken))
                .andExpect(status().isOk());

        assertThat(cropRepository.findById(saved.getId())).isEmpty();
    }
}
