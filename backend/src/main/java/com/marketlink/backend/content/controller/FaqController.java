package com.marketlink.backend.content.controller;

import com.marketlink.backend.common.response.ApiResponse;
import com.marketlink.backend.content.dto.FaqDto;
import com.marketlink.backend.content.service.ContentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/faqs")
@RequiredArgsConstructor
public class FaqController {

    private final ContentService contentService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<FaqDto>>> getFaqs() {
        List<FaqDto> faqs = contentService.getAllFaqs();
        return ResponseEntity.ok(ApiResponse.success(faqs));
    }
}
