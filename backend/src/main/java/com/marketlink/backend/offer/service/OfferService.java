package com.marketlink.backend.offer.service;

import com.marketlink.backend.common.exception.ApiException;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.domain.offer.entity.Offer;
import com.marketlink.backend.domain.offer.enums.OfferStatus;
import com.marketlink.backend.domain.offer.repository.OfferRepository;
import com.marketlink.backend.domain.user.entity.BuyerProfile;
import com.marketlink.backend.domain.user.repository.BuyerProfileRepository;
import com.marketlink.backend.offer.dto.CreateOfferRequest;
import com.marketlink.backend.offer.dto.OfferResponse;
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
public class OfferService {

    private final OfferRepository offerRepository;
    private final LotRepository lotRepository;
    private final BuyerProfileRepository buyerProfileRepository;

    @Transactional
    public OfferResponse createOffer(UUID buyerId, UUID lotId, CreateOfferRequest request) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + lotId));

        if (lot.getFarmerId().equals(buyerId)) {
            throw new ApiException("Farmer cannot place an offer on their own produce lot", HttpStatus.BAD_REQUEST);
        }

        if (lot.getStatus() != LotStatus.PUBLISHED && lot.getStatus() != LotStatus.OFFER_RECEIVED) {
            throw new ApiException("Offers can only be placed on active PUBLISHED lots. Current lot status: " + lot.getStatus(),
                    HttpStatus.BAD_REQUEST);
        }

        if (request.getQuantity() > lot.getQuantity()) {
            throw new ApiException("Offered quantity (" + request.getQuantity() + ") exceeds available lot quantity (" + lot.getQuantity() + ")",
                    HttpStatus.BAD_REQUEST);
        }

        if (lot.getMinimumAcceptablePrice() != null && request.getOfferedPrice() < lot.getMinimumAcceptablePrice()) {
            throw new ApiException("Offered price must be at or above farmer's minimum acceptable price of ₹" + lot.getMinimumAcceptablePrice(),
                    HttpStatus.BAD_REQUEST);
        }

        Offer offer = Offer.builder()
                .lotId(lotId)
                .buyerId(buyerId)
                .offeredPrice(request.getOfferedPrice())
                .quantity(request.getQuantity())
                .status(OfferStatus.PENDING)
                .notes(request.getNotes())
                .build();

        Offer savedOffer = offerRepository.save(offer);

        // Update lot status to OFFER_RECEIVED if it was PUBLISHED
        if (lot.getStatus() == LotStatus.PUBLISHED) {
            lot.setStatus(LotStatus.OFFER_RECEIVED);
            lotRepository.save(lot);
            log.info("Lot {} transitioned to OFFER_RECEIVED upon offer {}", lotId, savedOffer.getId());
        }

        log.info("Buyer {} placed offer {} of ₹{} on lot {}", buyerId, savedOffer.getId(), request.getOfferedPrice(), lotId);
        return enrichResponse(savedOffer, lot);
    }

    @Transactional
    public OfferResponse acceptOffer(UUID farmerId, UUID offerId) {
        Offer offer = offerRepository.findById(offerId)
                .orElseThrow(() -> new ResourceNotFoundException("Offer not found with id: " + offerId));

        Lot lot = lotRepository.findById(offer.getLotId())
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + offer.getLotId()));

        if (!lot.getFarmerId().equals(farmerId)) {
            throw new ApiException("Not authorized: You are not the owner of this lot", HttpStatus.FORBIDDEN);
        }

        if (offer.getStatus() != OfferStatus.PENDING) {
            throw new ApiException("Only PENDING offers can be accepted. Current offer status: " + offer.getStatus(),
                    HttpStatus.BAD_REQUEST);
        }

        if (lot.getStatus() != LotStatus.PUBLISHED && lot.getStatus() != LotStatus.OFFER_RECEIVED) {
            throw new ApiException("Cannot accept offer on lot in status: " + lot.getStatus(), HttpStatus.BAD_REQUEST);
        }

        // Accept this offer
        offer.setStatus(OfferStatus.ACCEPTED);
        Offer savedOffer = offerRepository.save(offer);

        // Transition lot to ACCEPTED
        lot.setStatus(LotStatus.ACCEPTED);
        lotRepository.save(lot);
        log.info("Farmer {} accepted offer {} on lot {}. Lot transitioned to ACCEPTED", farmerId, offerId, lot.getId());

        // Automatically reject all other pending offers for this lot
        List<Offer> otherOffers = offerRepository.findByLotIdAndStatus(lot.getId(), OfferStatus.PENDING);
        for (Offer other : otherOffers) {
            if (!other.getId().equals(offerId)) {
                other.setStatus(OfferStatus.REJECTED);
                offerRepository.save(other);
                log.info("Auto-rejected pending offer {} on lot {}", other.getId(), lot.getId());
            }
        }

        return enrichResponse(savedOffer, lot);
    }

    @Transactional
    public OfferResponse rejectOffer(UUID farmerId, UUID offerId) {
        Offer offer = offerRepository.findById(offerId)
                .orElseThrow(() -> new ResourceNotFoundException("Offer not found with id: " + offerId));

        Lot lot = lotRepository.findById(offer.getLotId())
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + offer.getLotId()));

        if (!lot.getFarmerId().equals(farmerId)) {
            throw new ApiException("Not authorized: You are not the owner of this lot", HttpStatus.FORBIDDEN);
        }

        if (offer.getStatus() != OfferStatus.PENDING) {
            throw new ApiException("Only PENDING offers can be rejected. Current status: " + offer.getStatus(),
                    HttpStatus.BAD_REQUEST);
        }

        offer.setStatus(OfferStatus.REJECTED);
        Offer savedOffer = offerRepository.save(offer);
        log.info("Farmer {} rejected offer {} on lot {}", farmerId, offerId, lot.getId());

        // If no pending offers remain, check if lot should revert to PUBLISHED
        long remainingPending = offerRepository.countByLotIdAndStatus(lot.getId(), OfferStatus.PENDING);
        if (remainingPending == 0 && lot.getStatus() == LotStatus.OFFER_RECEIVED) {
            lot.setStatus(LotStatus.PUBLISHED);
            lotRepository.save(lot);
            log.info("Lot {} reverted to PUBLISHED since no pending offers remain", lot.getId());
        }

        return enrichResponse(savedOffer, lot);
    }

    @Transactional
    public OfferResponse cancelOffer(UUID buyerId, UUID offerId) {
        Offer offer = offerRepository.findById(offerId)
                .orElseThrow(() -> new ResourceNotFoundException("Offer not found with id: " + offerId));

        if (!offer.getBuyerId().equals(buyerId)) {
            throw new ApiException("Not authorized: You can only cancel your own offers", HttpStatus.FORBIDDEN);
        }

        if (offer.getStatus() != OfferStatus.PENDING) {
            throw new ApiException("Only PENDING offers can be cancelled. Current status: " + offer.getStatus(),
                    HttpStatus.BAD_REQUEST);
        }

        offer.setStatus(OfferStatus.CANCELLED);
        Offer savedOffer = offerRepository.save(offer);
        log.info("Buyer {} cancelled offer {}", buyerId, offerId);

        // Check if lot should revert to PUBLISHED
        Lot lot = lotRepository.findById(offer.getLotId()).orElse(null);
        if (lot != null && lot.getStatus() == LotStatus.OFFER_RECEIVED) {
            long remainingPending = offerRepository.countByLotIdAndStatus(lot.getId(), OfferStatus.PENDING);
            if (remainingPending == 0) {
                lot.setStatus(LotStatus.PUBLISHED);
                lotRepository.save(lot);
            }
        }

        return enrichResponse(savedOffer, lot);
    }

    @Transactional(readOnly = true)
    public List<OfferResponse> getOffersForLot(UUID callerId, UUID lotId) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + lotId));

        List<Offer> offers;
        if (lot.getFarmerId().equals(callerId)) {
            // Farmer sees all offers for their lot
            offers = offerRepository.findByLotIdOrderByCreatedAtDesc(lotId);
        } else {
            // Buyer sees only their own offers for this lot
            offers = offerRepository.findByLotIdOrderByCreatedAtDesc(lotId).stream()
                    .filter(o -> o.getBuyerId().equals(callerId))
                    .collect(Collectors.toList());
        }

        return offers.stream()
                .map(o -> enrichResponse(o, lot))
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<OfferResponse> getOffersByBuyer(UUID buyerId) {
        return offerRepository.findByBuyerIdOrderByCreatedAtDesc(buyerId).stream()
                .map(this::enrichResponse)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public OfferResponse getOfferById(UUID callerId, UUID offerId) {
        Offer offer = offerRepository.findById(offerId)
                .orElseThrow(() -> new ResourceNotFoundException("Offer not found with id: " + offerId));

        Lot lot = lotRepository.findById(offer.getLotId())
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + offer.getLotId()));

        if (!offer.getBuyerId().equals(callerId) && !lot.getFarmerId().equals(callerId)) {
            throw new ApiException("Not authorized to view this offer", HttpStatus.FORBIDDEN);
        }

        return enrichResponse(offer, lot);
    }

    private OfferResponse enrichResponse(Offer offer) {
        Lot lot = lotRepository.findById(offer.getLotId()).orElse(null);
        return enrichResponse(offer, lot);
    }

    private OfferResponse enrichResponse(Offer offer, Lot lot) {
        OfferResponse response = OfferResponse.fromEntity(offer);
        if (lot != null) {
            response.setCropName(lot.getCropName());
            response.setUnit(lot.getUnit());
        }
        buyerProfileRepository.findById(offer.getBuyerId())
                .ifPresent(bp -> response.setBuyerBusinessName(bp.getBusinessName()));
        return response;
    }
}
