package com.marketlink.backend.marketprice;

import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.domain.crop.entity.Crop;
import com.marketlink.backend.domain.crop.repository.CropRepository;
import com.marketlink.backend.domain.market.entity.Market;
import com.marketlink.backend.domain.market.repository.MarketRepository;
import com.marketlink.backend.domain.marketprice.entity.MarketPrice;
import com.marketlink.backend.domain.marketprice.repository.MarketPriceRepository;
import com.marketlink.backend.marketprice.dto.MarketPriceResponse;
import com.marketlink.backend.marketprice.dto.RecordMarketPriceRequest;
import com.marketlink.backend.marketprice.service.MarketPriceService;
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
class MarketPriceServiceTest {

    @Mock
    private MarketPriceRepository marketPriceRepository;

    @Mock
    private CropRepository cropRepository;

    @Mock
    private MarketRepository marketRepository;

    @InjectMocks
    private MarketPriceService marketPriceService;

    private UUID cropId;
    private UUID marketId;
    private Crop sampleCrop;
    private Market sampleMarket;
    private MarketPrice samplePrice;

    @BeforeEach
    void setUp() {
        cropId = UUID.randomUUID();
        marketId = UUID.randomUUID();

        sampleCrop = Crop.builder()
                .id(cropId)
                .name("ONION")
                .unit("QUINTAL")
                .build();

        sampleMarket = Market.builder()
                .id(marketId)
                .name("Pune APMC")
                .district("Pune")
                .state("Maharashtra")
                .build();

        samplePrice = MarketPrice.builder()
                .id(UUID.randomUUID())
                .cropId(cropId)
                .marketId(marketId)
                .priceDate(LocalDate.now())
                .minPrice(1800.0)
                .maxPrice(2600.0)
                .modalPrice(2200.0)
                .arrivalQuantity(450.0)
                .unit("QUINTAL")
                .source("APMC_AGMARKNET")
                .createdAt(Instant.now())
                .build();
    }

    @Test
    @DisplayName("Record market price successfully when constraints are valid")
    void testRecordMarketPrice_Success() {
        RecordMarketPriceRequest request = RecordMarketPriceRequest.builder()
                .cropId(cropId)
                .marketId(marketId)
                .priceDate(LocalDate.now())
                .minPrice(1800.0)
                .maxPrice(2600.0)
                .modalPrice(2200.0)
                .arrivalQuantity(450.0)
                .unit("QUINTAL")
                .build();

        when(cropRepository.findById(cropId)).thenReturn(Optional.of(sampleCrop));
        when(marketRepository.findById(marketId)).thenReturn(Optional.of(sampleMarket));
        when(marketPriceRepository.save(any(MarketPrice.class))).thenReturn(samplePrice);

        MarketPriceResponse response = marketPriceService.recordMarketPrice(request);

        assertThat(response).isNotNull();
        assertThat(response.getCropName()).isEqualTo("ONION");
        assertThat(response.getMarketName()).isEqualTo("Pune APMC");
        assertThat(response.getModalPrice()).isEqualTo(2200.0);
    }

    @Test
    @DisplayName("Reject price record if minPrice > maxPrice")
    void testRecordMarketPrice_InvalidMinMax() {
        RecordMarketPriceRequest request = RecordMarketPriceRequest.builder()
                .cropId(cropId)
                .marketId(marketId)
                .minPrice(3000.0)
                .maxPrice(2000.0)
                .modalPrice(2500.0)
                .build();

        when(cropRepository.findById(cropId)).thenReturn(Optional.of(sampleCrop));
        when(marketRepository.findById(marketId)).thenReturn(Optional.of(sampleMarket));

        assertThatThrownBy(() -> marketPriceService.recordMarketPrice(request))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("Minimum price cannot exceed maximum price");

        verify(marketPriceRepository, never()).save(any(MarketPrice.class));
    }

    @Test
    @DisplayName("Reject price record if modalPrice is outside [minPrice, maxPrice]")
    void testRecordMarketPrice_InvalidModalPrice() {
        RecordMarketPriceRequest request = RecordMarketPriceRequest.builder()
                .cropId(cropId)
                .marketId(marketId)
                .minPrice(1800.0)
                .maxPrice(2600.0)
                .modalPrice(3000.0)
                .build();

        when(cropRepository.findById(cropId)).thenReturn(Optional.of(sampleCrop));
        when(marketRepository.findById(marketId)).thenReturn(Optional.of(sampleMarket));

        assertThatThrownBy(() -> marketPriceService.recordMarketPrice(request))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("Modal price must be between minimum and maximum price");
    }

    @Test
    @DisplayName("Get latest market price returns most recent observation")
    void testGetLatestMarketPrice() {
        when(marketPriceRepository.findFirstByCropIdAndMarketIdOrderByPriceDateDesc(cropId, marketId))
                .thenReturn(Optional.of(samplePrice));
        when(cropRepository.findById(cropId)).thenReturn(Optional.of(sampleCrop));
        when(marketRepository.findById(marketId)).thenReturn(Optional.of(sampleMarket));

        MarketPriceResponse response = marketPriceService.getLatestMarketPrice(cropId, marketId);

        assertThat(response).isNotNull();
        assertThat(response.getModalPrice()).isEqualTo(2200.0);
        assertThat(response.getCropName()).isEqualTo("ONION");
    }
}
