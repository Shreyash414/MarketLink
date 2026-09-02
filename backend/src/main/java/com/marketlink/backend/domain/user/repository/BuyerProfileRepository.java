package com.marketlink.backend.domain.user.repository;

import com.marketlink.backend.domain.user.entity.BuyerProfile;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface BuyerProfileRepository extends JpaRepository<BuyerProfile, UUID> {
    Optional<BuyerProfile> findByUserId(UUID userId);
    void deleteByUserId(UUID userId);
}
