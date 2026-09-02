package com.marketlink.backend.marketplace.service;

import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.marketplace.entity.Bid;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.BidStatus;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.BidRepository;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.marketplace.dto.AcceptBidRequest;
import com.marketlink.backend.marketplace.dto.CreateLotRequest;
import com.marketlink.backend.marketplace.dto.LotResponseDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class MarketplaceLotService {

    private final LotRepository lotRepository;
    private final BidRepository bidRepository;

    @Transactional
    public LotResponseDto createLot(UUID farmerId, CreateLotRequest request) {
        Lot lot = Lot.builder()
                .farmerId(farmerId)
                .cropName(request.getCropName())
                .variety(request.getVariety())
                .quantity(request.getQuantityKg())
                .expectedPrice(request.getBasePricePerKg())
                .status(LotStatus.DRAFT)
                .location(request.getLocation())
                .build();

        lot = lotRepository.save(lot);
        log.info("Farmer {} created lot {}", farmerId, lot.getId());
        return LotResponseDto.fromEntity(lot);
    }

    @Transactional
    public LotResponseDto publishLot(UUID farmerId, UUID lotId) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found"));

        if (!lot.getFarmerId().equals(farmerId)) {
            throw new ApiException("Not authorized to publish this lot", HttpStatus.FORBIDDEN);
        }

        lot.setStatus(LotStatus.PUBLISHED);
        lot = lotRepository.save(lot);
        log.info("Farmer {} published lot {}", farmerId, lotId);
        return LotResponseDto.fromEntity(lot);
    }

    @Transactional
    public LotResponseDto acceptBid(UUID farmerId, UUID lotId, AcceptBidRequest request) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found"));

        if (!lot.getFarmerId().equals(farmerId)) {
            throw new ApiException("Not authorized to manage this lot", HttpStatus.FORBIDDEN);
        }

        Bid bid = bidRepository.findById(request.getBidId())
                .orElseThrow(() -> new ResourceNotFoundException("Bid not found"));

        if (!bid.getLotId().equals(lotId)) {
            throw new ApiException("Bid does not correspond to this lot", HttpStatus.BAD_REQUEST);
        }

        if (request.getConfirmationPin() == null || request.getConfirmationPin().isBlank()) {
            throw new ApiException("Confirmation PIN required to accept bid", HttpStatus.BAD_REQUEST);
        }

        bid.setStatus(BidStatus.ACCEPTED);
        bidRepository.save(bid);

        lot.setStatus(LotStatus.SOLD);
        lot = lotRepository.save(lot);

        log.info("Farmer {} accepted bid {} for lot {}", farmerId, bid.getId(), lotId);
        return LotResponseDto.fromEntity(lot);
    }

    @Transactional(readOnly = true)
    public List<LotResponseDto> getFarmerLots(UUID farmerId) {
        return lotRepository.findByFarmerIdOrderByCreatedAtDesc(farmerId).stream()
                .map(LotResponseDto::fromEntity)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<LotResponseDto> getPublishedLots() {
        return lotRepository.findByStatusOrderByCreatedAtDesc(LotStatus.PUBLISHED).stream()
                .map(LotResponseDto::fromEntity)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public LotResponseDto getLotById(UUID lotId) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found"));
        return LotResponseDto.fromEntity(lot);
    }
}
