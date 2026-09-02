package com.marketlink.backend.marketplace.service;

import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.marketplace.entity.Bid;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.BidStatus;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.BidRepository;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.marketplace.dto.BidResponseDto;
import com.marketlink.backend.marketplace.dto.CreateBidRequest;
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
public class MarketplaceBidService {

    private final BidRepository bidRepository;
    private final LotRepository lotRepository;

    @Transactional
    public BidResponseDto createBid(UUID buyerId, CreateBidRequest request) {
        Lot lot = lotRepository.findById(request.getLotId())
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found"));

        if (lot.getStatus() != LotStatus.PUBLISHED) {
            throw new ApiException("Cannot bid on a lot that is not PUBLISHED", HttpStatus.BAD_REQUEST);
        }

        Bid bid = Bid.builder()
                .lotId(request.getLotId())
                .buyerId(buyerId)
                .offeredPricePerKg(request.getOfferedPricePerKg())
                .totalQuantityKg(request.getTotalQuantityKg())
                .status(BidStatus.PENDING)
                .build();

        bid = bidRepository.save(bid);
        log.info("Buyer {} placed bid {} on lot {}", buyerId, bid.getId(), request.getLotId());
        return BidResponseDto.fromEntity(bid);
    }

    @Transactional(readOnly = true)
    public List<BidResponseDto> getBuyerBids(UUID buyerId) {
        return bidRepository.findByBuyerIdOrderByCreatedAtDesc(buyerId).stream()
                .map(BidResponseDto::fromEntity)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<BidResponseDto> getLotBids(UUID lotId) {
        return bidRepository.findByLotIdOrderByCreatedAtDesc(lotId).stream()
                .map(BidResponseDto::fromEntity)
                .collect(Collectors.toList());
    }
}
