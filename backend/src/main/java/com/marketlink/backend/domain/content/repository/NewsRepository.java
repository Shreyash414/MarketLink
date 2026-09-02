package com.marketlink.backend.domain.content.repository;

import com.marketlink.backend.domain.content.entity.NewsItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface NewsRepository extends JpaRepository<NewsItem, UUID> {
    List<NewsItem> findAllByOrderByPublishedAtDesc();
}
