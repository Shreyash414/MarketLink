package com.marketlink.backend.domain.user.repository;

import com.marketlink.backend.domain.user.entity.FarmerProfile;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface FarmerProfileRepository extends JpaRepository<FarmerProfile, UUID> {
    Optional<FarmerProfile> findByUserId(UUID userId);
    void deleteByUserId(UUID userId);
}
