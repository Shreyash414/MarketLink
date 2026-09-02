package com.marketlink.backend.domain.content.repository;

import com.marketlink.backend.domain.content.entity.FaqItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface FaqRepository extends JpaRepository<FaqItem, UUID> {
    List<FaqItem> findAllByOrderByDisplayOrderAsc();
}
