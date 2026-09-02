package com.marketlink.backend.market;

import com.marketlink.backend.common.exception.DuplicateResourceException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.market.entity.Market;
import com.marketlink.backend.domain.market.repository.MarketRepository;
import com.marketlink.backend.market.dto.CreateMarketRequest;
import com.marketlink.backend.market.dto.MarketResponse;
import com.marketlink.backend.market.dto.UpdateMarketRequest;
import com.marketlink.backend.market.service.MarketService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class MarketServiceTest {

    @Mock
    private MarketRepository marketRepository;

    @InjectMocks
    private MarketService marketService;

    private Market sampleMarket;
    private UUID marketId;

    @BeforeEach
    void setUp() {
        marketId = UUID.randomUUID();
        sampleMarket = Market.builder()
                .id(marketId)
                .name("Pune APMC")
                .district("Pune")
                .state("Maharashtra")
                .latitude(18.5204)
                .longitude(73.8567)
                .active(true)
                .createdAt(Instant.now())
                .updatedAt(Instant.now())
                .build();
    }

    @Test
    @DisplayName("Successfully create market when location is unique")
    void testCreateMarket_Success() {
        CreateMarketRequest request = CreateMarketRequest.builder()
                .name("Pune APMC")
                .district("Pune")
                .state("Maharashtra")
                .latitude(18.5204)
                .longitude(73.8567)
                .build();

        when(marketRepository.existsByNameIgnoreCaseAndDistrictIgnoreCaseAndStateIgnoreCase("Pune APMC", "Pune", "Maharashtra"))
                .thenReturn(false);
        when(marketRepository.save(any(Market.class))).thenReturn(sampleMarket);

        MarketResponse response = marketService.createMarket(request);

        assertThat(response).isNotNull();
        assertThat(response.getName()).isEqualTo("Pune APMC");
        assertThat(response.getDistrict()).isEqualTo("Pune");
        assertThat(response.getState()).isEqualTo("Maharashtra");
        assertThat(response.getLatitude()).isEqualTo(18.5204);

        verify(marketRepository).save(any(Market.class));
    }

    @Test
    @DisplayName("Throw DuplicateResourceException when market already exists in region")
    void testCreateMarket_Duplicate() {
        CreateMarketRequest request = CreateMarketRequest.builder()
                .name("Pune APMC")
                .district("Pune")
                .state("Maharashtra")
                .build();

        when(marketRepository.existsByNameIgnoreCaseAndDistrictIgnoreCaseAndStateIgnoreCase("Pune APMC", "Pune", "Maharashtra"))
                .thenReturn(true);

        assertThatThrownBy(() -> marketService.createMarket(request))
                .isInstanceOf(DuplicateResourceException.class)
                .hasMessageContaining("already exists");

        verify(marketRepository, never()).save(any(Market.class));
    }

    @Test
    @DisplayName("Get market by ID returns market when present")
    void testGetMarketById_Found() {
        when(marketRepository.findById(marketId)).thenReturn(Optional.of(sampleMarket));

        MarketResponse response = marketService.getMarketById(marketId);

        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo(marketId);
        assertThat(response.getName()).isEqualTo("Pune APMC");
    }

    @Test
    @DisplayName("Get market by ID throws ResourceNotFoundException when missing")
    void testGetMarketById_NotFound() {
        UUID unknownId = UUID.randomUUID();
        when(marketRepository.findById(unknownId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> marketService.getMarketById(unknownId))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessageContaining("Market not found with id: " + unknownId);
    }

    @Test
    @DisplayName("Get all markets filtered by state and district")
    void testGetAllMarkets_Filtered() {
        when(marketRepository.findByStateIgnoreCaseAndDistrictIgnoreCaseAndActiveTrueOrderByNameAsc("Maharashtra", "Pune"))
                .thenReturn(List.of(sampleMarket));

        List<MarketResponse> results = marketService.getAllMarkets("Maharashtra", "Pune", true);

        assertThat(results).hasSize(1);
        assertThat(results.get(0).getName()).isEqualTo("Pune APMC");
    }

    @Test
    @DisplayName("Update market successfully modifies properties")
    void testUpdateMarket_Success() {
        UpdateMarketRequest request = UpdateMarketRequest.builder()
                .name("Pune Central APMC")
                .latitude(18.5300)
                .build();

        when(marketRepository.findById(marketId)).thenReturn(Optional.of(sampleMarket));
        when(marketRepository.existsByNameIgnoreCaseAndDistrictIgnoreCaseAndStateIgnoreCaseAndIdNot(
                "Pune Central APMC", "Pune", "Maharashtra", marketId)).thenReturn(false);
        when(marketRepository.save(any(Market.class))).thenAnswer(inv -> inv.getArgument(0));

        MarketResponse response = marketService.updateMarket(marketId, request);

        assertThat(response.getName()).isEqualTo("Pune Central APMC");
        assertThat(response.getLatitude()).isEqualTo(18.5300);
    }
}
