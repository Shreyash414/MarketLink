package com.marketlink.backend.domain.image.repository;

import com.marketlink.backend.domain.image.entity.LotImage;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface LotImageRepository extends MongoRepository<LotImage, UUID> {

    List<LotImage> findByLotIdOrderByCreatedAtDesc(UUID lotId);

    List<LotImage> findByLotId(UUID lotId);

    Optional<LotImage> findByIdAndLotId(UUID id, UUID lotId);

    void deleteByIdAndLotId(UUID id, UUID lotId);

    void deleteByLotId(UUID lotId);
}
