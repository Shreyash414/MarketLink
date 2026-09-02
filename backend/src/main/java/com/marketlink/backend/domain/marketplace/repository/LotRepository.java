package com.marketlink.backend.domain.marketplace.repository;

import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface LotRepository extends JpaRepository<Lot, UUID> {

    List<Lot> findByFarmerIdOrderByCreatedAtDesc(UUID farmerId);

    List<Lot> findByStatusOrderByCreatedAtDesc(LotStatus status);

    List<Lot> findByStatusInOrderByCreatedAtDesc(List<LotStatus> statuses);

    List<Lot> findByCropIdAndStatusInOrderByCreatedAtDesc(UUID cropId, List<LotStatus> statuses);

    List<Lot> findByMarketIdAndStatusInOrderByCreatedAtDesc(UUID marketId, List<LotStatus> statuses);

    List<Lot> findByCropIdAndMarketIdAndStatusInOrderByCreatedAtDesc(UUID cropId, UUID marketId, List<LotStatus> statuses);
}
