package com.marketlink.backend.domain.crop.repository;

import com.marketlink.backend.domain.crop.entity.Crop;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface CropRepository extends JpaRepository<Crop, UUID> {

    Optional<Crop> findByNameIgnoreCase(String name);

    boolean existsByNameIgnoreCase(String name);

    boolean existsByNameIgnoreCaseAndIdNot(String name, UUID id);

    List<Crop> findByActiveTrueOrderByNameAsc();

    List<Crop> findByCategoryIgnoreCaseAndActiveTrueOrderByNameAsc(String category);

    List<Crop> findByCategoryIgnoreCaseOrderByNameAsc(String category);
}
