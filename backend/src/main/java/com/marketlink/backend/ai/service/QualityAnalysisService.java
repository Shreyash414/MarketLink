package com.marketlink.backend.ai.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.marketlink.backend.ai.adapter.QualityModelAdapter;
import com.marketlink.backend.ai.dto.QualityAnalysisResponse;
import com.marketlink.backend.ai.dto.RecordQualityResultRequest;
import com.marketlink.backend.common.exception.ResourceNotFoundException;
import com.marketlink.backend.domain.marketplace.entity.Lot;
import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import com.marketlink.backend.domain.marketplace.repository.LotRepository;
import com.marketlink.backend.domain.quality.entity.QualityAnalysisResult;
import com.marketlink.backend.domain.quality.enums.QualityAnalysisStatus;
import com.marketlink.backend.domain.quality.repository.QualityAnalysisResultRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class QualityAnalysisService {

    private final QualityAnalysisResultRepository qualityRepository;
    private final LotRepository lotRepository;
    private final List<QualityModelAdapter> adapters;
    private final ObjectMapper objectMapper;

    @Transactional
    public QualityAnalysisResponse recordQualityResult(UUID lotId, RecordQualityResultRequest request) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + lotId));

        QualityAnalysisResult result;

        if (request.getRawPayload() != null) {
            result = adaptRawPayload(lotId, request.getModelProvider(), request.getRawPayload());
        } else {
            String attrsJson = "{}";
            if (request.getAttributes() != null && !request.getAttributes().isEmpty()) {
                try {
                    attrsJson = objectMapper.writeValueAsString(request.getAttributes());
                } catch (Exception ignored) {}
            }

            result = QualityAnalysisResult.builder()
                    .lotId(lotId)
                    .status(QualityAnalysisStatus.COMPLETED)
                    .qualityScore(request.getQualityScore())
                    .grade(request.getGrade() != null ? request.getGrade().toUpperCase() : "STANDARD")
                    .confidence(request.getConfidence() != null ? request.getConfidence() : 1.0)
                    .modelProvider(request.getModelProvider() != null ? request.getModelProvider() : "DIRECT_ENTRY")
                    .modelVersion(request.getModelVersion() != null ? request.getModelVersion() : "v1.0")
                    .attributesJson(attrsJson)
                    .analyzedAt(Instant.now())
                    .build();
        }

        QualityAnalysisResult savedResult = qualityRepository.save(result);
        log.info("Saved quality analysis result: id={}, lotId={}, grade={}, score={}",
                savedResult.getId(), lotId, savedResult.getGrade(), savedResult.getQualityScore());

        // Update lot status if in DRAFT or QUALITY_PENDING
        if (lot.getStatus() == LotStatus.DRAFT || lot.getStatus() == LotStatus.QUALITY_PENDING) {
            lot.setStatus(LotStatus.QUALITY_VERIFIED);
            lotRepository.save(lot);
            log.info("Lot {} transitioned to QUALITY_VERIFIED", lotId);
        }

        return QualityAnalysisResponse.fromEntity(savedResult);
    }

    @Transactional
    public QualityAnalysisResponse processExternalModelResponse(UUID lotId, String modelProvider, Object rawModelOutput) {
        Lot lot = lotRepository.findById(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("Lot not found with id: " + lotId));

        QualityAnalysisResult result = adaptRawPayload(lotId, modelProvider, rawModelOutput);
        QualityAnalysisResult savedResult = qualityRepository.save(result);

        if (result.getStatus() == QualityAnalysisStatus.COMPLETED &&
                (lot.getStatus() == LotStatus.DRAFT || lot.getStatus() == LotStatus.QUALITY_PENDING)) {
            lot.setStatus(LotStatus.QUALITY_VERIFIED);
            lotRepository.save(lot);
            log.info("Lot {} transitioned to QUALITY_VERIFIED after AI processing", lotId);
        }

        return QualityAnalysisResponse.fromEntity(savedResult);
    }

    @Transactional(readOnly = true)
    public QualityAnalysisResponse getLatestQualityResult(UUID lotId) {
        if (!lotRepository.existsById(lotId)) {
            throw new ResourceNotFoundException("Lot not found with id: " + lotId);
        }
        QualityAnalysisResult result = qualityRepository.findFirstByLotIdOrderByAnalyzedAtDesc(lotId)
                .orElseThrow(() -> new ResourceNotFoundException("No quality analysis found for lot: " + lotId));
        return QualityAnalysisResponse.fromEntity(result);
    }

    @Transactional(readOnly = true)
    public List<QualityAnalysisResponse> getAllQualityResultsForLot(UUID lotId) {
        if (!lotRepository.existsById(lotId)) {
            throw new ResourceNotFoundException("Lot not found with id: " + lotId);
        }
        return qualityRepository.findByLotIdOrderByAnalyzedAtDesc(lotId).stream()
                .map(QualityAnalysisResponse::fromEntity)
                .collect(Collectors.toList());
    }

    private QualityAnalysisResult adaptRawPayload(UUID lotId, String modelProvider, Object rawPayload) {
        for (QualityModelAdapter adapter : adapters) {
            if (adapter.supports(modelProvider)) {
                return adapter.adapt(lotId, rawPayload);
            }
        }
        // Fallback
        return adapters.getLast().adapt(lotId, rawPayload);
    }
}
