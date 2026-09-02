package com.marketlink.backend.content.service;

import com.marketlink.backend.content.dto.FaqDto;
import com.marketlink.backend.content.dto.NewsDto;
import com.marketlink.backend.domain.content.entity.FaqItem;
import com.marketlink.backend.domain.content.entity.NewsItem;
import com.marketlink.backend.domain.content.repository.FaqRepository;
import com.marketlink.backend.domain.content.repository.NewsRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ContentService {

    private final NewsRepository newsRepository;
    private final FaqRepository faqRepository;

    @PostConstruct
    public void seedInitialContent() {
        if (newsRepository.count() == 0) {
            newsRepository.save(NewsItem.builder()
                    .title("Monsoon Crop Advisory 2026")
                    .summary("Key recommendations for Kharif crop cultivation and soil moisture management.")
                    .content("Farmers are advised to prepare soil beds and monitor weather forecasts closely...")
                    .category("Advisory")
                    .publishedAt(Instant.now())
                    .build());

            newsRepository.save(NewsItem.builder()
                    .title("Market Mandi Price Updates")
                    .summary("Wheat and paddy prices stabilize across major agricultural mandis.")
                    .content("Trading volumes have increased with transparent digital bidding...")
                    .category("Market Trends")
                    .publishedAt(Instant.now().minusSeconds(86400))
                    .build());
        }

        if (faqRepository.count() == 0) {
            faqRepository.save(FaqItem.builder()
                    .question("How do I verify my identity on MarketLink?")
                    .answer("Go to Identity Verification in your profile, enter your Aadhaar reference details, and verify with the OTP.")
                    .category("Verification")
                    .displayOrder(1)
                    .build());

            faqRepository.save(FaqItem.builder()
                    .question("What can I do with a Basic Account before verification?")
                    .answer("You can read daily agricultural news, access FAQs, update your personal profile, and complete identity verification.")
                    .category("Account")
                    .displayOrder(2)
                    .build());
        }
    }

    @Transactional(readOnly = true)
    public List<NewsDto> getAllNews() {
        return newsRepository.findAllByOrderByPublishedAtDesc().stream()
                .map(NewsDto::fromEntity)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<FaqDto> getAllFaqs() {
        return faqRepository.findAllByOrderByDisplayOrderAsc().stream()
                .map(FaqDto::fromEntity)
                .collect(Collectors.toList());
    }
}
