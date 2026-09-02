
package com.marketlink.backend.market.service;

import com.marketlink.backend.common.exception.DuplicateResourceException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.market.entity.Market;
import com.marketlink.backend.domain.market.repository.MarketRepository;
import com.marketlink.backend.market.dto.CreateMarketRequest;
import com.marketlink.backend.market.dto.MarketResponse;
import com.marketlink.backend.market.dto.UpdateMarketRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class MarketService {

    private final MarketRepository marketRepository;

    @Transactional
    public MarketResponse createMarket(CreateMarketRequest request) {
        String name = request.getName().trim();
        String district = request.getDistrict().trim();
        String state = request.getState().trim();

        if (marketRepository.existsByNameIgnoreCaseAndDistrictIgnoreCaseAndStateIgnoreCase(name, district, state)) {
            throw new DuplicateResourceException(
                    String.format("Market '%s' already exists in district '%s', state '%s'", name, district, state));
        }

        Market market = Market.builder()
                .name(name)
                .district(district)
                .state(state)
                .latitude(request.getLatitude())
                .longitude(request.getLongitude())
                .active(true)
                .build();

        Market savedMarket = marketRepository.save(market);
        log.info("Created new market record: id={}, name={}, district={}, state={}",
                savedMarket.getId(), savedMarket.getName(), savedMarket.getDistrict(), savedMarket.getState());
        return MarketResponse.fromEntity(savedMarket);
    }

    @Transactional(readOnly = true)
    public MarketResponse getMarketById(UUID id) {
        Market market = marketRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Market not found with id: " + id));
        return MarketResponse.fromEntity(market);
    }

    @Transactional(readOnly = true)
    public List<MarketResponse> getAllMarkets(String state, String district, Boolean activeOnly) {
        List<Market> markets;
        boolean filterActive = (activeOnly == null || activeOnly);

        boolean hasState = state != null && !state.isBlank();
        boolean hasDistrict = district != null && !district.isBlank();

        if (hasState && hasDistrict) {
            String s = state.trim();
            String d = district.trim();
            if (filterActive) {
                markets = marketRepository.findByStateIgnoreCaseAndDistrictIgnoreCaseAndActiveTrueOrderByNameAsc(s, d);
            } else {
                markets = marketRepository.findByStateIgnoreCaseAndDistrictIgnoreCaseOrderByNameAsc(s, d);
            }
        } else if (hasState) {
            String s = state.trim();
            if (filterActive) {
                markets = marketRepository.findByStateIgnoreCaseAndActiveTrueOrderByNameAsc(s);
            } else {
                markets = marketRepository.findByStateIgnoreCaseOrderByNameAsc(s);
            }
        } else if (hasDistrict) {
            String d = district.trim();
            if (filterActive) {
                markets = marketRepository.findByDistrictIgnoreCaseAndActiveTrueOrderByNameAsc(d);
            } else {
                markets = marketRepository.findByDistrictIgnoreCaseOrderByNameAsc(d);
            }
        } else {
            if (filterActive) {
                markets = marketRepository.findByActiveTrueOrderByNameAsc();
            } else {
                markets = marketRepository.findAll();
            }
        }

        return markets.stream()
                .map(MarketResponse::fromEntity)
                .collect(Collectors.toList());
    }

    @Transactional
    public MarketResponse updateMarket(UUID id, UpdateMarketRequest request) {
        Market market = marketRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Market not found with id: " + id));

        String newName = request.getName() != null && !request.getName().isBlank() ? request.getName().trim() : market.getName();
        String newDistrict = request.getDistrict() != null && !request.getDistrict().isBlank() ? request.getDistrict().trim() : market.getDistrict();
        String newState = request.getState() != null && !request.getState().isBlank() ? request.getState().trim() : market.getState();

        if (marketRepository.existsByNameIgnoreCaseAndDistrictIgnoreCaseAndStateIgnoreCaseAndIdNot(newName, newDistrict, newState, id)) {
            throw new DuplicateResourceException(
                    String.format("Another market with name '%s' already exists in district '%s', state '%s'", newName, newDistrict, newState));
        }

        market.setName(newName);
        market.setDistrict(newDistrict);
        market.setState(newState);

        if (request.getLatitude() != null) {
            market.setLatitude(request.getLatitude());
        }
        if (request.getLongitude() != null) {
            market.setLongitude(request.getLongitude());
        }
        if (request.getActive() != null) {
            market.setActive(request.getActive());
        }

        Market updated = marketRepository.save(market);
        log.info("Updated market record: id={}, name={}", updated.getId(), updated.getName());
        return MarketResponse.fromEntity(updated);
    }

    @Transactional
    public void deleteMarket(UUID id) {
        Market market = marketRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Market not found with id: " + id));
        marketRepository.delete(market);
        log.info("Deleted market record: id={}", id);
    }
}
