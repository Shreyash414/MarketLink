package com.marketlink.backend.domain.quality.repository;

import com.marketlink.backend.domain.quality.entity.QualityAnalysisResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface QualityAnalysisResultRepository extends JpaRepository<QualityAnalysisResult, UUID> {

    List<QualityAnalysisResult> findByLotIdOrderByAnalyzedAtDesc(UUID lotId);

    Optional<QualityAnalysisResult> findFirstByLotIdOrderByAnalyzedAtDesc(UUID lotId);

    void deleteByLotId(UUID lotId);
}
