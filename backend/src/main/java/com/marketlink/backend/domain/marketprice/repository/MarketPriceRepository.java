package com.marketlink.backend.domain.marketprice.repository;

import com.marketlink.backend.domain.marketprice.entity.MarketPrice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface MarketPriceRepository extends JpaRepository<MarketPrice, UUID> {

    List<MarketPrice> findByCropIdAndMarketIdAndPriceDateBetweenOrderByPriceDateDesc(UUID cropId, UUID marketId, LocalDate startDate, LocalDate endDate);

    List<MarketPrice> findByCropIdAndPriceDateBetweenOrderByPriceDateDesc(UUID cropId, LocalDate startDate, LocalDate endDate);

    List<MarketPrice> findByMarketIdAndPriceDateBetweenOrderByPriceDateDesc(UUID marketId, LocalDate startDate, LocalDate endDate);

    List<MarketPrice> findByPriceDateBetweenOrderByPriceDateDesc(LocalDate startDate, LocalDate endDate);

    Optional<MarketPrice> findFirstByCropIdAndMarketIdOrderByPriceDateDesc(UUID cropId, UUID marketId);

    Optional<MarketPrice> findFirstByCropIdOrderByPriceDateDesc(UUID cropId);

    @Query("SELECT mp FROM MarketPrice mp WHERE " +
            "(:cropId IS NULL OR mp.cropId = :cropId) AND " +
            "(:marketId IS NULL OR mp.marketId = :marketId) AND " +
            "(:startDate IS NULL OR mp.priceDate >= :startDate) AND " +
            "(:endDate IS NULL OR mp.priceDate <= :endDate) " +
            "ORDER BY mp.priceDate DESC")
    List<MarketPrice> filterMarketPrices(
            @Param("cropId") UUID cropId,
            @Param("marketId") UUID marketId,
            @Param("startDate") LocalDate startDate,
            @Param("endDate") LocalDate endDate);
}
