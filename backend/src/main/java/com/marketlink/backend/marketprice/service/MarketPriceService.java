package com.marketlink.backend.marketprice.service;

import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.crop.entity.Crop;
import com.marketlink.backend.domain.crop.repository.CropRepository;
import com.marketlink.backend.domain.market.entity.Market;
import com.marketlink.backend.domain.market.repository.MarketRepository;
import com.marketlink.backend.domain.marketprice.entity.MarketPrice;
import com.marketlink.backend.domain.marketprice.repository.MarketPriceRepository;
import com.marketlink.backend.marketprice.dto.MarketPriceResponse;
import com.marketlink.backend.marketprice.dto.RecordMarketPriceRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class MarketPriceService {

    private final MarketPriceRepository marketPriceRepository;
    private final CropRepository cropRepository;
    private final MarketRepository marketRepository;

    @Transactional
    public MarketPriceResponse recordMarketPrice(RecordMarketPriceRequest request) {
        Crop crop = cropRepository.findById(request.getCropId())
                .orElseThrow(() -> new ResourceNotFoundException("Crop not found with id: " + request.getCropId()));

        Market market = marketRepository.findById(request.getMarketId())
                .orElseThrow(() -> new ResourceNotFoundException("Market not found with id: " + request.getMarketId()));

        if (request.getMinPrice() > request.getMaxPrice()) {
            throw new ApiException("Minimum price cannot exceed maximum price", HttpStatus.BAD_REQUEST);
        }

        if (request.getModalPrice() < request.getMinPrice() || request.getModalPrice() > request.getMaxPrice()) {
            throw new ApiException("Modal price must be between minimum and maximum price", HttpStatus.BAD_REQUEST);
        }

        LocalDate date = request.getPriceDate() != null ? request.getPriceDate() : LocalDate.now();
        String unit = request.getUnit() != null ? request.getUnit().trim().toUpperCase() : "QUINTAL";
        String source = request.getSource() != null ? request.getSource().trim() : "APMC_AGMARKNET";

        MarketPrice mp = MarketPrice.builder()
                .cropId(crop.getId())
                .marketId(market.getId())
                .priceDate(date)
                .minPrice(request.getMinPrice())
                .maxPrice(request.getMaxPrice())
                .modalPrice(request.getModalPrice())
                .arrivalQuantity(request.getArrivalQuantity())
                .unit(unit)
                .source(source)
                .build();

        MarketPrice saved = marketPriceRepository.save(mp);
        log.info("Recorded market price: id={}, crop={}, market={}, date={}, modalPrice={}",
                saved.getId(), crop.getName(), market.getName(), date, saved.getModalPrice());

        return enrichResponse(saved, crop, market);
    }

    @Transactional(readOnly = true)
    public MarketPriceResponse getMarketPriceById(UUID id) {
        MarketPrice mp = marketPriceRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Market price record not found with id: " + id));
        return enrichResponse(mp);
    }

    @Transactional(readOnly = true)
    public List<MarketPriceResponse> queryMarketPrices(
            UUID cropId, UUID marketId, String state, String district, LocalDate startDate, LocalDate endDate) {

        List<MarketPrice> results;

        if (startDate == null && endDate == null) {
            // Default to last 30 days if no range provided
            startDate = LocalDate.now().minusDays(30);
            endDate = LocalDate.now();
        } else if (startDate != null && endDate != null && startDate.isAfter(endDate)) {
            throw new ApiException("startDate cannot be after endDate", HttpStatus.BAD_REQUEST);
        }

        results = marketPriceRepository.filterMarketPrices(cropId, marketId, startDate, endDate);

        // Filter by state and district if specified
        boolean filterRegion = (state != null && !state.isBlank()) || (district != null && !district.isBlank());
        Set<UUID> regionalMarketIds = null;
        if (filterRegion) {
            List<Market> markets = marketRepository.findAll();
            regionalMarketIds = markets.stream()
                    .filter(m -> state == null || state.isBlank() || m.getState().equalsIgnoreCase(state.trim()))
                    .filter(m -> district == null || district.isBlank() || m.getDistrict().equalsIgnoreCase(district.trim()))
                    .map(Market::getId)
                    .collect(Collectors.toSet());
        }

        final Set<UUID> validMarketIds = regionalMarketIds;
        return results.stream()
                .filter(mp -> validMarketIds == null || validMarketIds.contains(mp.getMarketId()))
                .map(this::enrichResponse)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public MarketPriceResponse getLatestMarketPrice(UUID cropId, UUID marketId) {
        if (cropId == null) {
            throw new ApiException("cropId is required to fetch latest market price", HttpStatus.BAD_REQUEST);
        }

        MarketPrice mp;
        if (marketId != null) {
            mp = marketPriceRepository.findFirstByCropIdAndMarketIdOrderByPriceDateDesc(cropId, marketId)
                    .orElseThrow(() -> new ResourceNotFoundException(
                            "No price data found for crop: " + cropId + " in market: " + marketId));
        } else {
            mp = marketPriceRepository.findFirstByCropIdOrderByPriceDateDesc(cropId)
                    .orElseThrow(() -> new ResourceNotFoundException(
                            "No price data found for crop: " + cropId));
        }

        return enrichResponse(mp);
    }

    private MarketPriceResponse enrichResponse(MarketPrice mp) {
        MarketPriceResponse response = MarketPriceResponse.fromEntity(mp);
        cropRepository.findById(mp.getCropId()).ifPresent(c -> response.setCropName(c.getName()));
        marketRepository.findById(mp.getMarketId()).ifPresent(m -> {
            response.setMarketName(m.getName());
            response.setDistrict(m.getDistrict());
            response.setState(m.getState());
        });
        return response;
    }

    private MarketPriceResponse enrichResponse(MarketPrice mp, Crop crop, Market market) {
        MarketPriceResponse response = MarketPriceResponse.fromEntity(mp);
        if (crop != null) {
            response.setCropName(crop.getName());
        }
        if (market != null) {
            response.setMarketName(market.getName());
            response.setDistrict(market.getDistrict());
            response.setState(market.getState());
        }
        return response;
    }
}
