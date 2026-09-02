package com.marketlink.backend.domain.offer.repository;

import com.marketlink.backend.domain.offer.entity.Offer;
import com.marketlink.backend.domain.offer.enums.OfferStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface OfferRepository extends JpaRepository<Offer, UUID> {

    List<Offer> findByLotIdOrderByCreatedAtDesc(UUID lotId);

    List<Offer> findByBuyerIdOrderByCreatedAtDesc(UUID buyerId);

    List<Offer> findByLotIdAndStatus(UUID lotId, OfferStatus status);

    Optional<Offer> findFirstByLotIdAndBuyerIdAndStatus(UUID lotId, UUID buyerId, OfferStatus status);

    long countByLotIdAndStatus(UUID lotId, OfferStatus status);
}
