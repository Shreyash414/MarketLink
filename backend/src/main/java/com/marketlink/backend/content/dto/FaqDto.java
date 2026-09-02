package com.marketlink.backend.content.dto;

import com.marketlink.backend.domain.content.entity.FaqItem;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FaqDto {
    private UUID id;
    private String question;
    private String answer;
    private String category;
    private Integer displayOrder;

    public static FaqDto fromEntity(FaqItem item) {
        return FaqDto.builder()
                .id(item.getId())
                .question(item.getQuestion())
                .answer(item.getAnswer())
                .category(item.getCategory())
                .displayOrder(item.getDisplayOrder())
                .build();
    }
}
