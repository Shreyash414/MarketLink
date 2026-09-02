package com.marketlink.backend.domain.marketplace.entity;

import com.marketlink.backend.domain.marketplace.enums.LotStatus;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "marketplace_lots", indexes = {
        @Index(name = "idx_lot_farmer_id", columnList = "farmerId"),
        @Index(name = "idx_lot_crop_id", columnList = "cropId"),
        @Index(name = "idx_lot_market_id", columnList = "marketId"),
        @Index(name = "idx_lot_status", columnList = "status"),
        @Index(name = "idx_lot_created_at", columnList = "createdAt")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Lot {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private UUID farmerId;

    private UUID cropId;

    @Column(nullable = false, length = 100)
    private String cropName;

    private UUID marketId;

    private String variety;

    @Column(nullable = false)
    private Double quantity;

    @Column(nullable = false, length = 20)
    @Builder.Default
    private String unit = "KG";

    private LocalDate harvestDate;

    @Column(nullable = false)
    private Double expectedPrice;

    private Double minimumAcceptablePrice;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 25)
    @Builder.Default
    private LotStatus status = LotStatus.DRAFT;

    private String location;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant updatedAt;

    // Backward compatibility helper methods for Phase 1 code/tests
    public Double getQuantityKg() {
        return this.quantity;
    }

    public void setQuantityKg(Double quantityKg) {
        this.quantity = quantityKg;
    }

    public Double getBasePricePerKg() {
        return this.expectedPrice;
    }

    public void setBasePricePerKg(Double basePrice) {
        this.expectedPrice = basePrice;
    }

    @PrePersist
    protected void onCreate() {
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        if (this.status == null) {
            this.status = LotStatus.DRAFT;
        }
        if (this.unit == null || this.unit.isBlank()) {
            this.unit = "KG";
        }
    }

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = Instant.now();
    }

    public static class LotBuilder {
        public LotBuilder quantityKg(Double quantityKg) {
            this.quantity = quantityKg;
            return this;
        }

        public LotBuilder basePricePerKg(Double basePricePerKg) {
            this.expectedPrice = basePricePerKg;
            return this;
        }
    }
}
