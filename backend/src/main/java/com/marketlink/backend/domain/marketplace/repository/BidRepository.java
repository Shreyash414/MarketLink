package com.marketlink.backend.domain.marketplace.repository;

import com.marketlink.backend.domain.marketplace.entity.Bid;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface BidRepository extends JpaRepository<Bid, UUID> {
    List<Bid> findByLotIdOrderByCreatedAtDesc(UUID lotId);
    List<Bid> findByBuyerIdOrderByCreatedAtDesc(UUID buyerId);
}
