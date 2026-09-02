package com.marketlink.backend.content.dto;

import com.marketlink.backend.domain.content.entity.NewsItem;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NewsDto {
    private UUID id;
    private String title;
    private String summary;
    private String content;
    private String category;
    private Instant publishedAt;

    public static NewsDto fromEntity(NewsItem item) {
        return NewsDto.builder()
                .id(item.getId())
                .title(item.getTitle())
                .summary(item.getSummary())
                .content(item.getContent())
                .category(item.getCategory())
                .publishedAt(item.getPublishedAt())
                .build();
    }
}
