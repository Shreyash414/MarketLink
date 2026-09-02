package com.marketlink.backend.lot.service;

import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.crop.entity.Crop;
import com.marketlink.backend.domain.crop.repository.CropRepository;
import com.marketlink.backend.domain.market.entity.Market;
import com.marketlink.backend.domain.market.repository.MarketRepository;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.lot.dto.CreateLotRequest;
import com.marketlink.backend.lot.dto.LotResponse;
import com.marketlink.backend.lot.dto.UpdateLotRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class LotService {

    private final LotRepository lotRepository;
    private final CropRepository cropRepository;
    private final MarketRepository marketRepository;

    @Transactional
    public LotResponse createLot(UUID farmerId, CreateLotRequest request) {
        String resolvedCropName;
        UUID resolvedCropId = request.getCropId();
        String resolvedUnit = request.getUnit() != null ? request.getUnit().trim().toUpperCase() : "KG";

        if (resolvedCropId != null) {
            Crop crop = cropRepository.findById(resolvedCropId)
                    .orElseThrow(() -> new ResourceNotFoundException("Crop not found with id: " + request.getCropId()));
            resolvedCropName = crop.getName();
            if (request.getUnit() == null || request.getUnit().isBlank()) {
                resolvedUnit = crop.getUnit();
            }
        } else if (request.getCropName() != null && !request.getCropName().isBlank()) {
            String trimmedName = request.getCropName().trim();
            Optional<Crop> cropOpt = cropRepository.findByNameIgnoreCase(trimmedName);
            if (cropOpt.isPresent()) {
                Crop crop = cropOpt.get();
                resolvedCropId = crop.getId();
                resolvedCropName = crop.getName();
                if (request.getUnit() == null || request.getUnit().isBlank()) {
                    resolvedUnit = crop.getUnit();
                }
            } else {
                resolvedCropName = trimmedName.toUpperCase();
            }
        } else {
            throw new ApiException("Either cropId or cropName must be provided", HttpStatus.BAD_REQUEST);
        }

        UUID marketId = request.getMarketId();
        if (marketId != null) {
            marketRepository.findById(marketId)
                    .orElseThrow(() -> new ResourceNotFoundException("Market not found with id: " + marketId));
        }

        if (request.getMinimumAcceptablePrice() != null && request.getExpectedPrice() != null) {
            if (request.getMinimumAcceptablePrice() > request.getExpectedPrice()) {
                throw new ApiException("Minimum acceptable price cannot be higher than expected price", HttpStatus.BAD_REQUEST);
            }
        }

        Lot lot = Lot.builder()
                .farmerId(farmerId)
                .cropId(resolvedCropId)
                .cropName(resolvedCropName)
                .marketId(marketId)
                .variety(request.getVariety())
                .quantity(request.getQuantity())
                .unit(resolvedUnit)
                .harvestDate(request.getHarvestDate())
                .expectedPrice(request.getExpectedPrice())
                .minimumAcceptablePrice(request.getMinimumAcceptablePrice())
                .status(LotStatus.DRAFT)
                .location(request.getLocation())
                .build();

        Lot savedLot = lotRepository.save(lot);
        log.info("Farmer {} created new lot {} for crop {}", farmerId, savedLot.getId(), resolvedCropName);
        return mapToLotResponse(savedLot);
    }

    @Transactional(readOnly = true)
    public LotResponse getLotById(UUID lotId) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + lotId));
        return mapToLotResponse(lot);
    }

    @Transactional(readOnly = true)
    public List<LotResponse> getFarmerLots(UUID farmerId) {
        return lotRepository.findByFarmerIdOrderByCreatedAtDesc(farmerId).stream()
                .map(this::mapToLotResponse)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<LotResponse> getPublishedLots(UUID cropId, UUID marketId, Double minPrice, Double maxPrice) {
        List<LotStatus> activeStatuses = List.of(LotStatus.PUBLISHED, LotStatus.OFFER_RECEIVED);
        List<Lot> lots;

        if (cropId != null && marketId != null) {
            lots = lotRepository.findByCropIdAndMarketIdAndStatusInOrderByCreatedAtDesc(cropId, marketId, activeStatuses);
        } else if (cropId != null) {
            lots = lotRepository.findByCropIdAndStatusInOrderByCreatedAtDesc(cropId, activeStatuses);
        } else if (marketId != null) {
            lots = lotRepository.findByMarketIdAndStatusInOrderByCreatedAtDesc(marketId, activeStatuses);
        } else {
            lots = lotRepository.findByStatusInOrderByCreatedAtDesc(activeStatuses);
        }

        return lots.stream()
                .filter(lot -> minPrice == null || lot.getExpectedPrice() >= minPrice)
                .filter(lot -> maxPrice == null || lot.getExpectedPrice() <= maxPrice)
                .map(this::mapToLotResponse)
                .collect(Collectors.toList());
    }

    @Transactional
    public LotResponse updateLot(UUID farmerId, UUID lotId, UpdateLotRequest request) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + lotId));

        if (!lot.getFarmerId().equals(farmerId)) {
            throw new ApiException("Not authorized to modify this lot", HttpStatus.FORBIDDEN);
        }

        if (lot.getStatus() != LotStatus.DRAFT) {
            throw new ApiException("Only lots in DRAFT status can be modified", HttpStatus.BAD_REQUEST);
        }

        if (request.getCropId() != null) {
            Crop crop = cropRepository.findById(request.getCropId())
                    .orElseThrow(() -> new ResourceNotFoundException("Crop not found with id: " + request.getCropId()));
            lot.setCropId(crop.getId());
            lot.setCropName(crop.getName());
        } else if (request.getCropName() != null && !request.getCropName().isBlank()) {
            lot.setCropName(request.getCropName().trim().toUpperCase());
        }

        if (request.getMarketId() != null) {
            marketRepository.findById(request.getMarketId())
                    .orElseThrow(() -> new ResourceNotFoundException("Market not found with id: " + request.getMarketId()));
            lot.setMarketId(request.getMarketId());
        }

        if (request.getVariety() != null) {
            lot.setVariety(request.getVariety());
        }
        if (request.getQuantity() != null) {
            lot.setQuantity(request.getQuantity());
        }
        if (request.getUnit() != null && !request.getUnit().isBlank()) {
            lot.setUnit(request.getUnit().trim().toUpperCase());
        }
        if (request.getHarvestDate() != null) {
            lot.setHarvestDate(request.getHarvestDate());
        }
        if (request.getExpectedPrice() != null) {
            lot.setExpectedPrice(request.getExpectedPrice());
        }
        if (request.getMinimumAcceptablePrice() != null) {
            lot.setMinimumAcceptablePrice(request.getMinimumAcceptablePrice());
        }
        if (request.getLocation() != null) {
            lot.setLocation(request.getLocation());
        }

        if (lot.getMinimumAcceptablePrice() != null && lot.getExpectedPrice() != null) {
            if (lot.getMinimumAcceptablePrice() > lot.getExpectedPrice()) {
                throw new ApiException("Minimum acceptable price cannot be higher than expected price", HttpStatus.BAD_REQUEST);
            }
        }

        Lot updated = lotRepository.save(lot);
        log.info("Farmer {} updated draft lot {}", farmerId, lotId);
        return mapToLotResponse(updated);
    }

    @Transactional
    public LotResponse publishLot(UUID farmerId, UUID lotId) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + lotId));

        if (!lot.getFarmerId().equals(farmerId)) {
            throw new ApiException("Not authorized to publish this lot", HttpStatus.FORBIDDEN);
        }

        if (lot.getStatus() != LotStatus.DRAFT && lot.getStatus() != LotStatus.QUALITY_VERIFIED) {
            throw new ApiException(
                    String.format("Cannot publish lot in status '%s'. Lot must be in DRAFT or QUALITY_VERIFIED.", lot.getStatus()),
                    HttpStatus.BAD_REQUEST);
        }

        lot.setStatus(LotStatus.PUBLISHED);
        Lot published = lotRepository.save(lot);
        log.info("Farmer {} published lot {}", farmerId, lotId);
        return mapToLotResponse(published);
    }

    @Transactional
    public LotResponse closeLot(UUID farmerId, UUID lotId) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + lotId));

        if (!lot.getFarmerId().equals(farmerId)) {
            throw new ApiException("Not authorized to close this lot", HttpStatus.FORBIDDEN);
        }

        if (lot.getStatus() == LotStatus.CLOSED || lot.getStatus() == LotStatus.CANCELLED) {
            throw new ApiException(String.format("Lot is already %s", lot.getStatus()), HttpStatus.BAD_REQUEST);
        }

        lot.setStatus(LotStatus.CLOSED);
        Lot closed = lotRepository.save(lot);
        log.info("Farmer {} closed lot {}", farmerId, lotId);
        return mapToLotResponse(closed);
    }

    @Transactional
    public LotResponse cancelLot(UUID farmerId, UUID lotId) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + lotId));

        if (!lot.getFarmerId().equals(farmerId)) {
            throw new ApiException("Not authorized to cancel this lot", HttpStatus.FORBIDDEN);
        }

        if (lot.getStatus() == LotStatus.ACCEPTED || lot.getStatus() == LotStatus.SOLD || lot.getStatus() == LotStatus.CLOSED) {
            throw new ApiException("Cannot cancel an accepted, sold, or closed lot", HttpStatus.BAD_REQUEST);
        }

        lot.setStatus(LotStatus.CANCELLED);
        Lot cancelled = lotRepository.save(lot);
        log.info("Farmer {} cancelled lot {}", farmerId, lotId);
        return mapToLotResponse(cancelled);
    }

    private LotResponse mapToLotResponse(Lot lot) {
        LotResponse response = LotResponse.fromEntity(lot);
        if (lot.getMarketId() != null) {
            Optional<Market> marketOpt = marketRepository.findById(lot.getMarketId());
            if (marketOpt.isPresent()) {
                response.setMarketName(marketOpt.get().getName());
            }
        }
        return response;
    }
}
