package com.marketlink.backend.domain.content.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "news_items")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class NewsItem {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private String title;

    @Column(length = 1000)
    private String summary;

    @Column(columnDefinition = "TEXT")
    private String content;

    private String category;

    @Column(nullable = false)
    private Instant publishedAt;

    @PrePersist
    protected void onCreate() {
        if (this.publishedAt == null) {
            this.publishedAt = Instant.now();
        }
    }
}
