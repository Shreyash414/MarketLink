package com.marketlink.backend.domain.market.repository;

import com.marketlink.backend.domain.market.entity.Market;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface MarketRepository extends JpaRepository<Market, UUID> {

    List<Market> findByNameIgnoreCase(String name);

    List<Market> findByActiveTrueOrderByNameAsc();

    List<Market> findByStateIgnoreCaseAndActiveTrueOrderByNameAsc(String state);

    List<Market> findByStateIgnoreCaseAndDistrictIgnoreCaseAndActiveTrueOrderByNameAsc(String state, String district);

    List<Market> findByDistrictIgnoreCaseAndActiveTrueOrderByNameAsc(String district);

    List<Market> findByStateIgnoreCaseAndDistrictIgnoreCaseOrderByNameAsc(String state, String district);

    List<Market> findByStateIgnoreCaseOrderByNameAsc(String state);

    List<Market> findByDistrictIgnoreCaseOrderByNameAsc(String district);

    Optional<Market> findByNameIgnoreCaseAndDistrictIgnoreCaseAndStateIgnoreCase(String name, String district, String state);

    boolean existsByNameIgnoreCaseAndDistrictIgnoreCaseAndStateIgnoreCase(String name, String district, String state);

    boolean existsByNameIgnoreCaseAndDistrictIgnoreCaseAndStateIgnoreCaseAndIdNot(String name, String district, String state, UUID id);
}
