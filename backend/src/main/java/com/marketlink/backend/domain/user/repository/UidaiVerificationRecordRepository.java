package com.marketlink.backend.domain.user.repository;

import com.marketlink.backend.domain.user.entity.UidaiVerificationRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface UidaiVerificationRecordRepository extends JpaRepository<UidaiVerificationRecord, UUID> {
    Optional<UidaiVerificationRecord> findByTransactionId(String transactionId);
    Optional<UidaiVerificationRecord> findTopByUserIdOrderByCreatedAtDesc(UUID userId);
}
