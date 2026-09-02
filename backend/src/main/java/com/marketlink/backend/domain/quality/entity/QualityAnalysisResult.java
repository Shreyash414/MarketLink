package com.marketlink.backend.domain.quality.entity;

import com.marketlink.backend.domain.quality.enums.QualityAnalysisStatus;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "quality_analysis_results", indexes = {
        @Index(name = "idx_quality_result_lot_id", columnList = "lotId"),
        @Index(name = "idx_quality_result_status", columnList = "status")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class QualityAnalysisResult {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private UUID lotId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    @Builder.Default
    private QualityAnalysisStatus status = QualityAnalysisStatus.COMPLETED;

    private Double qualityScore;

    @Column(length = 50)
    private String grade;

    private Double confidence;

    @Column(length = 100)
    private String modelProvider;

    @Column(length = 50)
    private String modelVersion;

    @Column(columnDefinition = "TEXT")
    private String attributesJson;

    @Column(columnDefinition = "TEXT")
    private String rawMetadata;

    private Instant analyzedAt;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant updatedAt;

    @PrePersist
    protected void onCreate() {
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        if (this.analyzedAt == null) {
            this.analyzedAt = Instant.now();
        }
        if (this.status == null) {
            this.status = QualityAnalysisStatus.COMPLETED;
        }
    }

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = Instant.now();
    }
}
