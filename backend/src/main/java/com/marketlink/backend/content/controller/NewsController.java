package com.marketlink.backend.content.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.content.dto.NewsDto;
import com.marketlink.backend.content.service.ContentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/news")
@RequiredArgsConstructor
public class NewsController {

    private final ContentService contentService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<NewsDto>>> getNews() {
        List<NewsDto> news = contentService.getAllNews();
        return ResponseEntity.ok(ApiResponse.success(news));
    }
}
