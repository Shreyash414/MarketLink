package com.marketlink.backend.lot;

import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.crop.entity.Crop;
import com.marketlink.backend.domain.crop.repository.CropRepository;
import com.marketlink.backend.domain.market.repository.MarketRepository;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.lot.dto.CreateLotRequest;
import com.marketlink.backend.lot.dto.LotResponse;
import com.marketlink.backend.lot.dto.UpdateLotRequest;
import com.marketlink.backend.lot.service.LotService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class LotServiceTest {

    @Mock
    private LotRepository lotRepository;

    @Mock
    private CropRepository cropRepository;

    @Mock
    private MarketRepository marketRepository;

    @InjectMocks
    private LotService lotService;

    private UUID farmerId;
    private UUID lotId;
    private UUID cropId;
    private Crop sampleCrop;
    private Lot sampleLot;

    @BeforeEach
    void setUp() {
        farmerId = UUID.randomUUID();
        lotId = UUID.randomUUID();
        cropId = UUID.randomUUID();

        sampleCrop = Crop.builder()
                .id(cropId)
                .name("ONION")
                .category("VEGETABLE")
                .unit("KG")
                .active(true)
                .build();

        sampleLot = Lot.builder()
                .id(lotId)
                .farmerId(farmerId)
                .cropId(cropId)
                .cropName("ONION")
                .variety("Red Onion")
                .quantity(500.0)
                .unit("KG")
                .expectedPrice(35.0)
                .minimumAcceptablePrice(30.0)
                .status(LotStatus.DRAFT)
                .createdAt(Instant.now())
                .updatedAt(Instant.now())
                .build();
    }

    @Test
    @DisplayName("Create lot with valid cropId")
    void testCreateLot_WithCropId() {
        CreateLotRequest request = CreateLotRequest.builder()
                .cropId(cropId)
                .variety("Red Onion")
                .quantity(500.0)
                .expectedPrice(35.0)
                .minimumAcceptablePrice(30.0)
                .build();

        when(cropRepository.findById(cropId)).thenReturn(Optional.of(sampleCrop));
        when(lotRepository.save(any(Lot.class))).thenReturn(sampleLot);

        LotResponse response = lotService.createLot(farmerId, request);

        assertThat(response).isNotNull();
        assertThat(response.getCropName()).isEqualTo("ONION");
        assertThat(response.getStatus()).isEqualTo(LotStatus.DRAFT);
        assertThat(response.getQuantity()).isEqualTo(500.0);
    }

    @Test
    @DisplayName("Create lot throws exception when min price > expected price")
    void testCreateLot_InvalidPricing() {
        CreateLotRequest request = CreateLotRequest.builder()
                .cropName("ONION")
                .quantity(500.0)
                .expectedPrice(30.0)
                .minimumAcceptablePrice(35.0)
                .build();

        when(cropRepository.findByNameIgnoreCase("ONION")).thenReturn(Optional.of(sampleCrop));

        assertThatThrownBy(() -> lotService.createLot(farmerId, request))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("Minimum acceptable price cannot be higher");
    }

    @Test
    @DisplayName("Publish lot transitions status from DRAFT to PUBLISHED")
    void testPublishLot_Success() {
        when(lotRepository.findById(lotId)).thenReturn(Optional.of(sampleLot));
        when(lotRepository.save(any(Lot.class))).thenAnswer(inv -> inv.getArgument(0));

        LotResponse response = lotService.publishLot(farmerId, lotId);

        assertThat(response.getStatus()).isEqualTo(LotStatus.PUBLISHED);
    }

    @Test
    @DisplayName("Publish lot fails if not called by owner")
    void testPublishLot_Unauthorized() {
        UUID otherFarmerId = UUID.randomUUID();
        when(lotRepository.findById(lotId)).thenReturn(Optional.of(sampleLot));

        assertThatThrownBy(() -> lotService.publishLot(otherFarmerId, lotId))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("Not authorized");
    }

    @Test
    @DisplayName("Update lot succeeds in DRAFT status")
    void testUpdateLot_DraftStatus() {
        UpdateLotRequest request = UpdateLotRequest.builder()
                .quantity(600.0)
                .expectedPrice(40.0)
                .build();

        when(lotRepository.findById(lotId)).thenReturn(Optional.of(sampleLot));
        when(lotRepository.save(any(Lot.class))).thenAnswer(inv -> inv.getArgument(0));

        LotResponse response = lotService.updateLot(farmerId, lotId, request);

        assertThat(response.getQuantity()).isEqualTo(600.0);
        assertThat(response.getExpectedPrice()).isEqualTo(40.0);
    }

    @Test
    @DisplayName("Update lot fails if lot is already PUBLISHED")
    void testUpdateLot_AlreadyPublished() {
        sampleLot.setStatus(LotStatus.PUBLISHED);
        UpdateLotRequest request = UpdateLotRequest.builder()
                .quantity(600.0)
                .build();

        when(lotRepository.findById(lotId)).thenReturn(Optional.of(sampleLot));

        assertThatThrownBy(() -> lotService.updateLot(farmerId, lotId, request))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("Only lots in DRAFT status can be modified");
    }

    @Test
    @DisplayName("Close lot transitions status to CLOSED")
    void testCloseLot() {
        sampleLot.setStatus(LotStatus.PUBLISHED);
        when(lotRepository.findById(lotId)).thenReturn(Optional.of(sampleLot));
        when(lotRepository.save(any(Lot.class))).thenAnswer(inv -> inv.getArgument(0));

        LotResponse response = lotService.closeLot(farmerId, lotId);

        assertThat(response.getStatus()).isEqualTo(LotStatus.CLOSED);
    }
}
